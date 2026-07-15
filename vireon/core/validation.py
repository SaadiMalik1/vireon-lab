import time
import json
import logging
import math
from pathlib import Path
import numpy as np
from typing import Dict, List, Optional, Tuple, Any

"""
VIREON Automated Validation Suite

Loads real EEG datasets (EDF format) and synthetic attack traces,
feeds them through the SecurityEngine pipeline, and produces computed
benchmark metrics. Zero external dependencies beyond numpy.
"""
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Validation Runner
# ---------------------------------------------------------------------------
class ValidationRunner:
    """
    Automated validation pipeline that exercises the SecurityEngine against
    real and synthetic datasets to produce computed benchmark metrics.
    """

    def __init__(self, data_dir: str = "datasets"):
        self.data_dir = Path(data_dir)
        self.synthetic_dir = self.data_dir / "synthetic"
        self.results: List[Dict] = []

    def _load_profile(self, dataset_name: str) -> Optional[Dict]:
        import yaml
        profile_path = Path("profiles") / f"{dataset_name}.yaml"
        if profile_path.exists():
            with open(profile_path, "r") as f:
                return yaml.safe_load(f)
        return None

    def _calculate_wilson_ci(self, p: float, n: int, z: float = 1.96) -> Tuple[float, float]:
        """Calculates the Wilson score interval for a binomial proportion."""
        if n == 0:
            return 0.0, 0.0
        # Effective Sample Size correction (ESS) for autocorrelation
        n_eff = max(1.0, n / 10.0) 
        denominator = 1 + z**2 / n_eff
        center = (p + z**2 / (2 * n_eff)) / denominator
        spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * n_eff)) / n_eff) / denominator
        return max(0.0, center - spread), min(1.0, center + spread)

    def _compute_roc_metrics(self, y_true: List[int], y_score: List[float]) -> Dict:
        """
        Computes ROC curve, true AUC (trapezoidal), optimal operating point (Youden's J),
        and Wilson CIs symmetrically.
        """
        if not y_true:
            return {}
            
        y_true_np = np.array(y_true)
        y_score_np = np.array(y_score)
        
        # Sort scores descending
        desc_score_indices = np.argsort(y_score_np, kind="mergesort")[::-1]
        y_score_np = y_score_np[desc_score_indices]
        y_true_np = y_true_np[desc_score_indices]
        
        distinct_value_indices = np.where(np.diff(y_score_np))[0]
        threshold_idxs = np.r_[distinct_value_indices, y_true_np.size - 1]
        
        tps = np.cumsum(y_true_np)[threshold_idxs]
        fps = np.cumsum(1 - y_true_np)[threshold_idxs]
        
        total_p = tps[-1] if len(tps) > 0 else 0
        total_n = fps[-1] if len(fps) > 0 else 0
        
        if total_p == 0 or total_n == 0:
            return {"error": "Only one class present"}
            
        tpr = tps / total_p
        fpr = fps / total_n
        
        # Trapezoidal AUC
        try:
            auc = np.trapezoid(tpr, fpr)
        except AttributeError:
            auc = np.trapz(tpr, fpr) # type: ignore[attr-defined]
        
        # Youden's J optimal threshold
        j_stats = tpr - fpr
        optimal_idx = np.argmax(j_stats)
        
        opt_tpr = tpr[optimal_idx]
        opt_fpr = fpr[optimal_idx]
        
        opt_tp = tps[optimal_idx]
        opt_fp = fps[optimal_idx]
        opt_fn = total_p - opt_tp
        opt_tn = total_n - opt_fp
        
        precision = opt_tp / max(opt_tp + opt_fp, 1)
        f1 = (2 * precision * opt_tpr) / max(precision + opt_tpr, 1e-9)
        balanced_accuracy = (opt_tpr + (1 - opt_fpr)) / 2
        
        denom = math.sqrt((opt_tp + opt_fp) * (opt_tp + opt_fn) * (opt_tn + opt_fp) * (opt_tn + opt_fn))
        mcc = ((opt_tp * opt_tn) - (opt_fp * opt_fn)) / max(denom, 1e-9)
        
        fpr_low, fpr_high = self._calculate_wilson_ci(opt_fpr, total_n)
        tpr_low, tpr_high = self._calculate_wilson_ci(opt_tpr, total_p)
        
        return {
            "AUC": round(float(auc), 4),
            "Optimal_Threshold_Index": int(optimal_idx),
            "TP": int(opt_tp), "TN": int(opt_tn), "FP": int(opt_fp), "FN": int(opt_fn),
            "Recall": round(float(opt_tpr), 4),
            "Specificity": round(float(1 - opt_fpr), 4),
            "Precision": round(float(precision), 4),
            "F1": round(float(f1), 4),
            "Balanced_Accuracy": round(float(balanced_accuracy), 4),
            "MCC": round(float(mcc), 4),
            "FPR_95_CI": f"{fpr_low:.1%} - {fpr_high:.1%}",
            "Sensitivity_95_CI": f"{tpr_low:.1%} - {tpr_high:.1%}"
        }

    def _find_edf_files(self) -> List[Path]:
        edf_files = []
        for subdir in ['eeg', 'device']:
            d = self.data_dir / subdir
            if d.exists():
                edf_files.extend(sorted(d.glob("*.edf")))
        return edf_files

    def _load_synthetic(self) -> Dict:
        traces: Dict[str, Any] = {"baseline": None, "attacks": []}
        baseline_path = self.synthetic_dir / "normal" / "clean_baseline.json"
        if baseline_path.exists():
            with open(baseline_path) as f:
                traces["baseline"] = json.load(f)
        attack_dir = self.synthetic_dir / "attacks" / "held_out"
        if attack_dir.exists():
            for fp in sorted(attack_dir.glob("*.json")):
                with open(fp) as f:
                    traces["attacks"].append({"name": fp.stem, "data": json.load(f)})
        return traces

    def validate_ids_on_edf(self, edf_path: Path, max_seconds: float = 30.0) -> Dict:
        from vireon.core.twin import DigitalTwin
        from vireon.core.detection import SecurityEngine
        from vireon.core.attack import NoiseInjectionAttack, SignalDriftAttack

        logger.info(f"  Loading {edf_path.name}...")

        try:
            from vireon.plugins.datasets.edf_reader import EDFReader
            reader = EDFReader(str(edf_path), fallback_on_error=True)
            sample_rate = reader.sample_rate
            n_samples = reader.total_samples
            if n_samples < 0:
                n_samples = int((max_seconds or 30.0) * sample_rate)
            elif max_seconds is not None:
                n_samples = min(n_samples, int(max_seconds * sample_rate))
            data = reader.read_chunk(0, n_samples)
        except Exception as e:
            return {"file": edf_path.name, "status": "skipped", "error": str(e)}

        n_channels, n_samples = data.shape
        if n_channels == 0 or n_samples == 0:
            return {"file": edf_path.name, "status": "skipped", "error": "empty data"}

        logger.info(f"OK ({n_channels}ch, {sample_rate}Hz, {n_samples/sample_rate:.1f}s)")

        use_channels = min(n_channels, 8)
        data_subset = data[:use_channels, :]
        window_size = sample_rate
        n_windows = n_samples // window_size
        
        dataset_name = edf_path.stem.split('_')[0].lower()
        if 'sleep' in dataset_name:
            dataset_name = 'sleep_edf'
        profile = self._load_profile(dataset_name)
        
        calibration_windows = profile.get("calibration_windows", 5) if profile else min(10, n_windows // 3)

        if n_windows < 3:
            return {"file": edf_path.name, "status": "skipped", "error": "too few windows"}

        y_true = []
        y_score = []

        twin = DigitalTwin(sample_rate=sample_rate, num_channels=use_channels)
        ids_engine = SecurityEngine(twin)

        # Warmup
        for i in range(calibration_windows):
            window = data_subset[:, i * window_size : (i + 1) * window_size]
            ids_engine.analyze_signal(window)

        t_start = time.perf_counter()
        
        # Clean phase (Label 0)
        for i in range(calibration_windows, n_windows):
            window = data_subset[:, i * window_size : (i + 1) * window_size]
            score = ids_engine.score_signal(window)
            ids_engine.analyze_signal(window)  # keep EWMA advancing
            y_true.append(0)
            y_score.append(score)

        clean_latency_ms = ((time.perf_counter() - t_start) / max(len(y_true), 1)) * 1000

        # Noise Attack Phase (Label 1)
        noise_attack = NoiseInjectionAttack(target_channels=list(range(use_channels)), noise_level_microvolts=200.0)
        eeg_ch_list = list(range(use_channels))
        for i in range(calibration_windows, n_windows):
            window = data_subset[:, i * window_size : (i + 1) * window_size]
            attacked_window = noise_attack.apply(window, eeg_ch_list, sample_rate, twin)
            score = ids_engine.score_signal(attacked_window)
            y_true.append(1)
            y_score.append(score)

        # Drift Attack Phase (Label 1)
        drift_attack = SignalDriftAttack(target_channels=list(range(use_channels)), drift_rate_uv_per_sec=50.0)
        for i in range(calibration_windows, n_windows):
            window = data_subset[:, i * window_size : (i + 1) * window_size]
            attacked_window = drift_attack.apply(window, eeg_ch_list, sample_rate, twin)
            score = ids_engine.score_signal(attacked_window)
            y_true.append(1)
            y_score.append(score)

        stats = self._compute_roc_metrics(y_true, y_score)

        return {
            "file": edf_path.name,
            "status": "validated",
            "channels": n_channels,
            "sample_rate_hz": sample_rate,
            "duration_seconds": round(n_samples / sample_rate, 1),
            "windows_analyzed": len(y_true),
            "avg_latency_ms": round(clean_latency_ms, 2),
            **stats
        }

    def validate_synthetic(self) -> Dict:
        traces = self._load_synthetic()
        if not traces["baseline"]:
            return {"module": "synthetic", "status": "skipped", "error": "no synthetic data"}

        from vireon.core.twin import DigitalTwin
        from vireon.core.detection import SecurityEngine

        baseline_raw = traces["baseline"].get("data", traces["baseline"].get("samples", []))
        if not baseline_raw:
            return {"module": "synthetic", "status": "skipped", "error": "empty baseline"}

        data = np.array(baseline_raw).T if isinstance(baseline_raw[0], list) else np.array(baseline_raw).reshape(1, -1)

        twin = DigitalTwin(sample_rate=traces["baseline"].get("fs", 250), num_channels=data.shape[0])
        ids_engine = SecurityEngine(twin)

        y_true = []
        y_score = []

        # Analyze baseline window by window
        fs = traces["baseline"].get("fs", 250)
        n_samples = data.shape[1]
        window_size = fs
        n_windows = n_samples // window_size

        if n_windows == 0:
            return {"module": "synthetic", "status": "skipped", "error": "trace too short"}

        for i in range(n_windows):
            window = data[:, i*window_size : (i+1)*window_size]
            score = ids_engine.score_signal(window)
            ids_engine.analyze_signal(window) # advance state
            y_true.append(0)
            y_score.append(score)

        for attack_trace in traces["attacks"]:
            trace_json = attack_trace["data"]
            attack_raw = trace_json.get("data", trace_json.get("samples", []))
            if not attack_raw:
                continue
            attack_data = np.array(attack_raw).T if isinstance(attack_raw[0], list) else np.array(attack_raw).reshape(1, -1)
            
            # Restart twin/IDS for each attack to not carry over anomalous state
            twin_a = DigitalTwin(sample_rate=trace_json.get("fs", 250), num_channels=attack_data.shape[0])
            ids_a = SecurityEngine(twin_a)
            for i in range(min(n_windows, 5)):
                ids_a.analyze_signal(data[:, i*window_size : (i+1)*window_size])
                
            a_n_windows = attack_data.shape[1] // window_size
            for i in range(min(n_windows, 5), a_n_windows):
                window = attack_data[:, i*window_size : (i+1)*window_size]
                score = ids_a.score_signal(window)
                ids_a.analyze_signal(window)
                y_true.append(1)
                y_score.append(score)

        stats = self._compute_roc_metrics(y_true, y_score)
        
        return {
            "module": "synthetic_corpus",
            "status": "validated",
            "attacks_tested": len(traces["attacks"]),
            **stats
        }

    def run_all(self):
        logger.info("=" * 56)
        logger.info("  VIREON Automated Validation Suite")
        logger.info("=" * 56)

        logger.info("\n[1/2] Synthetic Attack Corpus")
        logger.info("-" * 40)
        synthetic_result = self.validate_synthetic()
        self.results.append(synthetic_result)

        if synthetic_result.get("status") == "validated":
            logger.info(f"  Attacks tested: {synthetic_result.get('attacks_tested', 0)}")
            logger.info(f"  AUC: {synthetic_result.get('AUC', 0):.3f}")
        else:
            logger.info(f"  SKIPPED: {synthetic_result.get('error', 'unknown')}")

        logger.info("\n[2/2] Real EDF Dataset Validation")
        logger.info("-" * 40)
        edf_files = self._find_edf_files()

        if not edf_files:
            logger.info("  No EDF files found. Only synthetic corpus was run.")
        else:
            for edf_path in edf_files:
                result = self.validate_ids_on_edf(edf_path, max_seconds=30.0)
                self.results.append(result)

                if result.get("status") == "validated":
                    logger.info(f"    AUC: {result.get('AUC', 0):.3f}  |  "
                          f"FP Rate: {result.get('FP', 0)/(result.get('FP', 0) + result.get('TN', 1)):.2%}  |  "
                          f"Sensitivity: {result.get('Recall', 0):.2%}  |  "
                          f"Latency: {result.get('avg_latency_ms', 0):.1f}ms")
                    logger.info(f"    [95% CIs] FPR: {result.get('FPR_95_CI')} | Sensitivity: {result.get('Sensitivity_95_CI')}")

        logger.info("\n" + "=" * 56)
        logger.info("  Validation Report (JSON)")
        logger.info("=" * 56)
        logger.info(json.dumps(self.results, indent=2))

        report_path = Path("datasets") / "validation_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"\n[+] Report saved to {report_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    runner = ValidationRunner()
    runner.run_all()
