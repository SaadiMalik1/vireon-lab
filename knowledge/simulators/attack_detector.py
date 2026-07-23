"""
VIREON-LABS NL-002 Lab 002: DSP-Based Neural Signal Attack Detection
================================================================

Implements non-cryptographic attack detection methods that use signal
processing to identify signal injection, replay, substitution, and
manipulation attacks on neural data.

Learning Objectives:
    1. Implement spectral anomaly detection using STFT
    2. Implement replay detection using temporal correlation analysis
    3. Implement injection detection using band-power consistency
    4. Understand the detection/performance trade-off for each method
    5. Produce detection metrics suitable for VIREON benchmarks

Required Software: Python 3.9+, numpy, scipy, matplotlib
Required Hardware: None
Estimated Time: 3-4 hours
Difficulty: Intermediate-Advanced

Usage:
    from attack_detector import AttackDetector, AttackScenario
    detector = AttackDetector(sampling_rate_hz=250.0)
    result = detector.detect(clean_signal, test_signal)
    print(result.summary())
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None

try:
    from scipy import signal as scipy_signal
    from scipy.stats import ks_2samp
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    scipy_signal = None
    ks_2samp = None




# ============================================================================
# Attack Scenarios
# ============================================================================

class AttackType(Enum):
    SINUSOIDAL_INJECTION = "sinusoidal_injection"
    REPLAY = "replay"
    SUBSTITUTION = "substitution"
    AMPLITUDE_SCALING = "amplitude_scaling"
    BROADBAND_NOISE = "broadband_noise"
    FEATURE_MANIPULATION = "feature_manipulation"
    COVERT_INJECTION = "covert_injection"


@dataclass
class AttackScenario:
    """Defines an attack to apply to a neural signal.
    
    Security Note:
        These scenarios correspond to the standardized attack
        scenarios defined in NL-002 Section 19.2 (AS-001 through AS-008).
    """
    attack_type: AttackType
    start_time_s: float
    duration_s: float
    params: dict = field(default_factory=dict)
    
    def apply(self, signal: np.ndarray, fs: float) -> np.ndarray:
        """Apply this attack to a signal. Returns modified copy."""
        attacked = signal.copy()
        start_idx = int(self.start_time_s * fs)
        end_idx = int((self.start_time_s + self.duration_s) * fs)
        end_idx = min(end_idx, len(attacked))
        segment = attacked[start_idx:end_idx]
        
        if self.attack_type == AttackType.SINUSOIDAL_INJECTION:
            freq = self.params.get("frequency_hz", 50.0)
            amplitude = self.params.get("amplitude_uv", 30.0)
            t = np.arange(len(segment)) / fs
            attacked[start_idx:end_idx] += amplitude * np.sin(2 * np.pi * freq * t)
        
        elif self.attack_type == AttackType.REPLAY:
            replay_offset = self.params.get("replay_offset_s", 2.0)
            replay_idx = int((self.start_time_s - replay_offset) * fs)
            replay_len = end_idx - start_idx
            if replay_idx >= 0 and replay_idx + replay_len <= len(signal):
                attacked[start_idx:end_idx] = signal[replay_idx:replay_idx + replay_len]
        
        elif self.attack_type == AttackType.SUBSTITUTION:
            sub_signal = self.params.get("substitute_signal", None)
            if sub_signal is not None:
                sub_len = min(len(segment), len(sub_signal))
                attacked[start_idx:start_idx + sub_len] = sub_signal[:sub_len]
        
        elif self.attack_type == AttackType.AMPLITUDE_SCALING:
            scale = self.params.get("scale_factor", 1.5)
            attacked[start_idx:end_idx] *= scale
        
        elif self.attack_type == AttackType.BROADBAND_NOISE:
            noise_rms = self.params.get("noise_rms_uv", 20.0)
            rng = np.random.default_rng(self.params.get("seed", 0))
            attacked[start_idx:end_idx] += rng.normal(0, noise_rms, len(segment))
        
        elif self.attack_type == AttackType.COVERT_INJECTION:
            freq = self.params.get("frequency_hz", 48.0)
            amplitude = self.params.get("amplitude_uv", 5.0)
            t = np.arange(len(segment)) / fs
            attacked[start_idx:end_idx] += amplitude * np.sin(2 * np.pi * freq * t)
        
        return attacked


# ============================================================================
# Detection Result
# ============================================================================

@dataclass
class DetectionResult:
    """Result of running attack detection."""
    attack_detected: bool
    detection_latency_s: float  # Time from attack start to detection
    confidence: float  # 0-1
    method: str
    details: dict = field(default_factory=dict)
    
    def summary(self) -> str:
        status = "DETECTED" if self.attack_detected else "NOT DETECTED"
        return (f"[{status}] {self.method}: confidence={self.confidence:.3f}, "
                f"latency={self.detection_latency_s:.3f}s")


# ============================================================================
# Attack Detector
# ============================================================================

class AttackDetector:
    """VIREON Attack Detection Provider.
    
    Implements multiple detection methods that can be composed:
    1. Spectral anomaly detection (STFT-based)
    2. Temporal correlation analysis (replay detection)
    3. Band power consistency (injection detection)
    4. Amplitude distribution analysis (substitution detection)
    5. Line noise monitoring (powerline injection)
    
    Design Principle:
        Each method produces a detection result with confidence.
        Results are combined using a voting/weighting scheme.
        No single method is sufficient — defense in depth.
    """

    def __init__(self, sampling_rate_hz: float, config: Optional[dict] = None) -> None:
        self.fs = sampling_rate_hz
        self.config = config or {}
        self.spectral_threshold_sigma = self.config.get("spectral_threshold_sigma", 3.0)
        self.replay_correlation_threshold = self.config.get("replay_correlation_threshold", 0.95)
        self.bandpower_change_threshold = self.config.get("bandpower_change_threshold", 0.5)  # 50% change

    # ------------------------------------------------------------------
    # Method 1: Spectral Anomaly Detection (STFT)
    # ------------------------------------------------------------------

    def detect_spectral_anomaly(self, clean: np.ndarray, test: np.ndarray,
                                 attack_start_s: float = 0.0) -> DetectionResult:
        """Detect attacks using STFT spectral comparison.
        
        Method:
            1. Compute STFT of clean and test signals
            2. Compute per-bin z-scores
            3. Flag bins exceeding threshold
            4. Analyze spatial pattern of flagged bins
        
        Security Strength:
            Effective against: sinusoidal injection, broadband noise,
            any attack that changes the spectral content.
            Weak against: replay (spectrally identical), in-band manipulation.
        """
        nperseg = min(256, len(clean) // 8)
        noverlap = nperseg // 2
        
        f_clean, t_clean, Zxx_clean = scipy_signal.stft(clean, self.fs, nperseg=nperseg, noverlap=noverlap)
        f_test, t_test, Zxx_test = scipy_signal.stft(test, self.fs, nperseg=nperseg, noverlap=noverlap)
        
        # Magnitude spectrograms (log-compressed)
        mag_clean = np.log1p(np.abs(Zxx_clean))
        mag_test = np.log1p(np.abs(Zxx_test))
        
        # Baseline statistics from clean signal
        mean_clean = np.mean(mag_clean, axis=1, keepdims=True)
        std_clean = np.std(mag_clean, axis=1, keepdims=True)
        std_clean = np.maximum(std_clean, 1e-10)  # Avoid division by zero
        
        # Z-score of test signal relative to clean baseline
        min_cols = min(mag_test.shape[1], mag_clean.shape[1])
        z_score = (mag_test[:, :min_cols] - mean_clean[:, :min_cols]) / std_clean[:, :min_cols]
        
        # Flag anomalous bins
        flagged = np.abs(z_score) > self.spectral_threshold_sigma
        
        # Temporal analysis: find first time point with significant anomaly
        anomaly_per_timepoint = np.sum(flagged, axis=0) / flagged.shape[0]
        attack_time_idx = None
        for i in range(len(anomaly_per_timepoint)):
            if anomaly_per_timepoint[i] > 0.05:  # 5% of frequency bins anomalous
                attack_time_idx = i
                break
        
        if attack_time_idx is not None:
            detected_time_s = t_test[attack_time_idx]
            latency = max(0, detected_time_s - attack_start_s)
            max_z = float(np.max(np.abs(z_score)))
            confidence = min(1.0, max_z / (self.spectral_threshold_sigma * 2))
            return DetectionResult(
                attack_detected=True,
                detection_latency_s=latency,
                confidence=confidence,
                method="spectral_anomaly",
                details={
                    "max_z_score": max_z,
                    "flagged_bin_fraction": float(anomaly_per_timepoint[attack_time_idx]),
                    "n_anomalous_timepoints": int(np.sum(anomaly_per_timepoint > 0.05)),
                },
            )
        
        return DetectionResult(
            attack_detected=False, detection_latency_s=0, confidence=0.0,
            method="spectral_anomaly",
        )

    # ------------------------------------------------------------------
    # Method 2: Replay Detection
    # ------------------------------------------------------------------

    def detect_replay(self, clean: np.ndarray, test: np.ndarray,
                      attack_start_s: float = 0.0) -> DetectionResult:
        """Detect replay attacks using temporal correlation analysis.
        
        Method:
            For each segment of the test signal, compute its maximum
            correlation with any segment of the clean signal. If the
            maximum correlation exceeds the threshold AND the matched
            segments are non-adjacent, flag as potential replay.
        
        Security Strength:
            Effective against: replay of recorded data.
            Weak against: synthetic signal generation, live injection.
            
        Limitation:
            Neural signals are stochastic — high correlation between
            non-replayed segments is possible by chance. The threshold
            must be set carefully to balance false positives.
        """
        seg_len = int(0.5 * self.fs)  # 500 ms segments
        if seg_len < 100 or len(clean) < 2 * seg_len or len(test) < seg_len:
            return DetectionResult(False, 0, 0, "replay_detection",
                                  {"reason": "signal too short"})
        
        start_idx = int(attack_start_s * self.fs)
        test_seg = test[start_idx:start_idx + seg_len]
        
        if len(test_seg) < seg_len:
            return DetectionResult(False, 0, 0, "replay_detection")
        
        # Compute correlation of test segment with all possible positions in clean
        correlations = []
        for offset in range(0, len(clean) - seg_len, seg_len // 2):
            clean_seg = clean[offset:offset + seg_len]
            corr = np.corrcoef(test_seg, clean_seg)[0, 1]
            if not np.isnan(corr):
                correlations.append((offset, corr))
        
        if not correlations:
            return DetectionResult(False, 0, 0, "replay_detection")
        
        max_corr = max(c for _, c in correlations)
        max_offset = [o for o, c in correlations if c == max_corr][0]
        
        # Check if the match is at a non-adjacent position (replay indicator)
        expected_offset = start_idx
        offset_distance = abs(max_offset - expected_offset) / self.fs
        is_nonadjacent = offset_distance > 1.0  # Match is > 1s away from expected
        
        if max_corr > self.replay_correlation_threshold and is_nonadjacent:
            return DetectionResult(
                attack_detected=True,
                detection_latency_s=0.0,  # Detected by analysis, not real-time
                confidence=float(max_corr),
                method="replay_detection",
                details={
                    "max_correlation": float(max_corr),
                    "match_offset_s": float(max_offset / self.fs),
                    "expected_offset_s": float(expected_offset / self.fs),
                    "offset_distance_s": float(offset_distance),
                },
            )
        
        return DetectionResult(
            attack_detected=False, detection_latency_s=0,
            confidence=float(max_corr),
            method="replay_detection",
            details={"max_correlation": float(max_corr)},
        )

    # ------------------------------------------------------------------
    # Method 3: Band Power Consistency
    # ------------------------------------------------------------------

    def detect_bandpower_anomaly(self, clean: np.ndarray, test: np.ndarray,
                                  attack_start_s: float = 0.0,
                                  bands: Optional[dict] = None) -> DetectionResult:
        """Detect attacks using band power consistency.
        
        Method:
            1. Compute band powers in sliding windows
            2. Compare test band powers against clean baseline
            3. Flag significant deviations
        
        Security Strength:
            Effective against: injection (changes band power),
            amplitude scaling (changes all band powers).
            Weak against: replay (same band powers), in-band attacks
            that preserve total band power.
        """
        if bands is None:
            bands = {"delta": (0.5, 4), "theta": (4, 8),
                    "alpha": (8, 13), "beta": (13, 30), "gamma": (30, 100)}
        
        win = int(1.0 * self.fs)  # 1-second windows
        step = win // 2
        
        if win > len(clean) or win > len(test):
            return DetectionResult(False, 0, 0, "bandpower_anomaly",
                                  {"reason": "signal too short"})
        
        # Compute clean baseline band powers
        nperseg = min(256, win // 2)
        f_clean, psd_clean = scipy_signal.welch(clean[:win], self.fs, nperseg=max(nperseg, 16))
        df = f_clean[1] - f_clean[0] if len(f_clean) > 1 else 1.0
        
        clean_bp = {}
        for band, (lo, hi) in bands.items():
            mask = (f_clean >= lo) & (f_clean <= hi)
            clean_bp[band] = float(np.sum(psd_clean[mask]) * df)
        
        # Scan test signal for band power anomalies
        start_idx = int(attack_start_s * self.fs)
        max_change = 0.0
        detected = False
        detected_time = 0.0
        details = {}
        
        for i in range(start_idx, len(test) - win, step):
            segment = test[i:i + win]
            f_seg, psd_seg = scipy_signal.welch(segment, self.fs, nperseg=max(nperseg, 16))
            
            changes = {}
            for band, (lo, hi) in bands.items():
                mask = (f_seg >= lo) & (f_seg <= hi)
                test_bp = float(np.sum(psd_seg[mask]) * df)
                if clean_bp[band] > 0:
                    change = abs(test_bp - clean_bp[band]) / clean_bp[band]
                    changes[band] = change
                    if change > self.bandpower_change_threshold:
                        detected = True
                        detected_time = i / self.fs
            
            if changes:
                max_change = max(max_change, max(changes.values()))
                details = changes
        
        if detected:
            latency = max(0, detected_time - attack_start_s)
            return DetectionResult(
                attack_detected=True,
                detection_latency_s=latency,
                confidence=min(1.0, max_change / 2.0),
                method="bandpower_anomaly",
                details={"band_changes": details, "max_change": max_change},
            )
        
        return DetectionResult(
            attack_detected=False, detection_latency_s=0,
            confidence=float(max_change),
            method="bandpower_anomaly",
            details={"band_changes": details},
        )

    # ------------------------------------------------------------------
    # Method 4: Amplitude Distribution Analysis
    # ------------------------------------------------------------------

    def detect_distribution_anomaly(self, clean: np.ndarray, test: np.ndarray,
                                     attack_start_s: float = 0.0) -> DetectionResult:
        """Detect substitution attacks using amplitude distribution comparison.
        
        Method: KS test between clean and test signal distributions.
        
        Security Strength:
            Effective against: substitution (different source has
            different amplitude distribution).
            Weak against: injection (distribution shifts but may
            not trigger KS test with short attack duration).
        """
        start_idx = int(attack_start_s * self.fs)
        test_segment = test[start_idx:]
        
        if len(test_segment) < 100 or len(clean) < 100:
            return DetectionResult(False, 0, 0, "distribution_anomaly",
                                  {"reason": "insufficient samples"})
        
        ks_stat, ks_p = ks_2samp(clean, test_segment)
        
        detected = ks_p < 0.01
        return DetectionResult(
            attack_detected=detected,
            detection_latency_s=0.0 if detected else 0.0,
            confidence=min(1.0, ks_stat * 5),
            method="distribution_anomaly",
            details={"ks_stat": float(ks_stat), "ks_p": float(ks_p)},
        )

    # ------------------------------------------------------------------
    # Combined Detection
    # ------------------------------------------------------------------

    def detect(self, clean: np.ndarray, test: np.ndarray,
               attack_start_s: float = 0.0) -> list[DetectionResult]:
        """Run all detection methods and return combined results.
        
        VIREON Defense-in-Depth:
            Multiple methods are run in parallel. An attack must evade
            ALL methods to go undetected. This is the core of VIREON's
            layered detection approach.
        """
        results = [
            self.detect_spectral_anomaly(clean, test, attack_start_s),
            self.detect_replay(clean, test, attack_start_s),
            self.detect_bandpower_anomaly(clean, test, attack_start_s),
            self.detect_distribution_anomaly(clean, test, attack_start_s),
        ]
        return results

    def detect_combined(self, clean: np.ndarray, test: np.ndarray,
                        attack_start_s: float = 0.0) -> DetectionResult:
        """Combine detection results using weighted voting.
        
        Any method detecting an attack with confidence > 0.5 triggers
        the combined detection. This ensures high sensitivity while
        maintaining reasonable false positive control.
        """
        results = self.detect(clean, test, attack_start_s)
        
        any_detected = any(r.attack_detected and r.confidence > 0.5 for r in results)
        max_confidence = max(r.confidence for r in results)
        min_latency = min((r.detection_latency_s for r in results if r.attack_detected), default=0)
        
        return DetectionResult(
            attack_detected=any_detected,
            detection_latency_s=min_latency,
            confidence=max_confidence,
            method="combined",
            details={
                "per_method": [
                    {"method": r.method, "detected": r.attack_detected,
                     "confidence": r.confidence, "latency": r.detection_latency_s}
                    for r in results
                ],
                "methods_triggered": sum(1 for r in results if r.attack_detected),
            },
        )

    # ------------------------------------------------------------------
    # Benchmark Mode
    # ------------------------------------------------------------------

    def run_benchmark(self, clean: np.ndarray,
                      scenarios: list[AttackScenario]) -> dict:
        """Run detection benchmark against multiple attack scenarios.
        
        Returns a benchmark result dict suitable for VIREON reporting.
        """
        benchmark_results = []
        
        for scenario in scenarios:
            attacked = scenario.apply(clean, self.fs)
            result = self.detect_combined(clean, attacked, scenario.start_time_s)
            
            benchmark_results.append({
                "attack_type": scenario.attack_type.value,
                "start_time_s": scenario.start_time_s,
                "duration_s": scenario.duration_s,
                "params": scenario.params,
                "detected": result.attack_detected,
                "confidence": result.confidence,
                "latency_s": result.detection_latency_s,
                "methods_triggered": result.details.get("methods_triggered", 0),
                "per_method": result.details.get("per_method", []),
            })
        
        # Summary statistics
        n_total = len(benchmark_results)
        n_detected = sum(1 for r in benchmark_results if r["detected"])
        detection_rate = n_detected / max(n_total, 1)
        avg_confidence = np.mean([r["confidence"] for r in benchmark_results])
        avg_latency = np.mean([r["latency_s"] for r in benchmark_results if r["detected"]]) if n_detected > 0 else 0
        
        return {
            "summary": {
                "total_scenarios": n_total,
                "detected": n_detected,
                "detection_rate": float(detection_rate),
                "avg_confidence": float(avg_confidence),
                "avg_latency_s": float(avg_latency),
            },
            "per_scenario": benchmark_results,
        }


# ============================================================================
# Main
# ============================================================================

def main() -> None:
    """Demo: run attack detection benchmark on synthetic EEG."""
    # Generate test signal
    fs = 250.0
    duration = 10.0
    n = int(duration * fs)
    t = np.arange(n) / fs
    rng = np.random.default_rng(42)
    
    clean = (30 * rng.standard_normal(n)
             + 20 * np.sin(2 * np.pi * 10 * t)
             + 15 * np.sin(2 * np.pi * 20 * t + rng.normal(0, 0.1, n).cumsum() / fs * 2 * np.pi))
    
    detector = AttackDetector(fs)
    
    # Define attack scenarios (from NL-002 Section 19.2)
    scenarios = [
        AttackScenario(AttackType.SINUSOIDAL_INJECTION, 5.0, 2.0,
                       {"frequency_hz": 50.0, "amplitude_uv": 30.0}),
        AttackScenario(AttackType.SINUSOIDAL_INJECTION, 5.0, 2.0,
                       {"frequency_hz": 15.0, "amplitude_uv": 10.0}),
        AttackScenario(AttackType.REPLAY, 5.0, 2.0,
                       {"replay_offset_s": 2.0}),
        AttackScenario(AttackType.AMPLITUDE_SCALING, 5.0, 2.0,
                       {"scale_factor": 1.5}),
        AttackScenario(AttackType.BROADBAND_NOISE, 5.0, 2.0,
                       {"noise_rms_uv": 20.0, "seed": 0}),
        AttackScenario(AttackType.COVERT_INJECTION, 5.0, 2.0,
                       {"frequency_hz": 48.0, "amplitude_uv": 5.0}),
    ]
    
    benchmark = detector.run_benchmark(clean, scenarios)
    
    print(f"{'='*60}")
    print("VIREON Attack Detection Benchmark")
    print(f"{'='*60}")
    s = benchmark["summary"]
    print(f"Scenarios: {s['total_scenarios']} | Detected: {s['detected']} | Rate: {s['detection_rate']:.1%}")
    print(f"Avg Confidence: {s['avg_confidence']:.3f} | Avg Latency: {s['avg_latency_s']:.3f}s")
    
    print(f"\n{'Type':<25} {'Detected':<10} {'Confidence':<12} {'Latency':<10} {'Methods'}")
    print("-" * 70)
    for r in benchmark["per_scenario"]:
        print(f"{r['attack_type']:<25} {str(r['detected']):<10} {r['confidence']:<12.3f} {r['latency_s']:<10.3f} {r['methods_triggered']}")
    
    # Export
    out_dir = "./output"
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "benchmark_results.json")
    with open(json_path, "w") as f:
        f.write(json.dumps(benchmark, indent=2, default=str))
    print(f"\nBenchmark exported: {json_path}")


if __name__ == "__main__":
    main()
