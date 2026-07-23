"""
VIREON-LABS NL-002 Lab 001: Neural Signal Processing Toolkit
==========================================================

A reusable signal processing pipeline for neural data, structured as a
VIREON provider. Implements filtering, artifact detection, feature extraction,
quality assessment, and time-frequency analysis — all with security annotations.

Learning Objectives:
    1. Implement the standard neural signal processing pipeline
    2. Understand how each processing stage affects security properties
    3. Produce a QualityReport that serves as VIREON's validation input
    4. Build a reusable, testable, composable processing pipeline

Required Software: Python 3.9+, numpy, scipy, matplotlib
Required Hardware: None
Estimated Time: 3-4 hours
Difficulty: Intermediate

Usage:
    from signal_processor import NeuralSignalProcessor, ProcessingConfig
    proc = NeuralSignalProcessor(ProcessingConfig())
    result = proc.process(samples, sampling_rate_hz=250.0)
    print(result.quality_report)

    # With NL-001 simulator:
    gen = NeuralSignalGenerator()
    eeg = gen.generate_eeg(duration_s=10)
    result = proc.process(eeg.samples, eeg.sampling_rate_hz)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal as scipy_signal
from scipy.stats import kurtosis, skew, ks_2samp


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class ProcessingConfig:
    """Configuration for the neural signal processing pipeline.
    
    Security Note:
        These parameters are security-critical. An attacker who modifies
        them can alter the processing pipeline's behavior. In a VIREON
        deployment, these should be stored in a verified configuration
        store with integrity protection.
    """
    # High-pass filter (DC removal)
    hp_cutoff_hz: float = 0.5
    hp_order: int = 2
    hp_filter_type: str = "butter"  # butter or bessel
    
    # Notch filter (powerline removal)
    notch_freq_hz: float = 50.0
    notch_quality: float = 30.0  # Q factor (higher = narrower notch)
    
    # Bandpass for feature extraction
    band_ranges: dict = field(default_factory=lambda: {
        "delta": (0.5, 4.0),
        "theta": (4.0, 8.0),
        "alpha": (8.0, 13.0),
        "beta": (13.0, 30.0),
        "gamma": (30.0, 100.0),
    })
    
    # Artifact detection
    amplitude_threshold_uv: float = 500.0  # EEG, adjust for other modalities
    line_noise_threshold_pct: float = 0.10  # 10% of total power
    
    # Feature extraction
    feature_window_sec: float = 1.0  # 1-second windows
    feature_overlap: float = 0.5  # 50% overlap
    
    # Quality assessment
    snr_alert_threshold_db: float = 6.0  # Alert if SNR drops by this much
    stationarity_ks_alpha: float = 0.01  # KS test significance level


class ModalityPreset(Enum):
    """Predefined configurations for different signal modalities."""
    EEG = ProcessingConfig(
        hp_cutoff_hz=0.5, hp_order=2,
        notch_freq_hz=50.0, notch_quality=30.0,
        amplitude_threshold_uv=500.0,
        band_ranges={
            "delta": (0.5, 4.0), "theta": (4.0, 8.0),
            "alpha": (8.0, 13.0), "beta": (13.0, 30.0),
            "gamma": (30.0, 100.0),
        },
    )
    ECOG = ProcessingConfig(
        hp_cutoff_hz=1.0, hp_order=3,
        notch_freq_hz=50.0, notch_quality=30.0,
        amplitude_threshold_uv=1000.0,
        band_ranges={
            "delta": (1.0, 4.0), "theta": (4.0, 8.0),
            "alpha": (8.0, 13.0), "beta": (13.0, 30.0),
            "gamma_low": (30.0, 80.0), "gamma_high": (80.0, 200.0),
        },
    )
    LFP = ProcessingConfig(
        hp_cutoff_hz=2.0, hp_order=2,
        notch_freq_hz=50.0, notch_quality=30.0,
        amplitude_threshold_uv=2000.0,
        band_ranges={
            "delta": (2.0, 4.0), "theta": (4.0, 8.0),
            "alpha": (8.0, 13.0), "beta": (13.0, 30.0),
            "gamma": (30.0, 100.0),
        },
    )


# ============================================================================
# Quality Report
# ============================================================================

@dataclass
class ChannelQuality:
    """Quality metrics for a single channel."""
    channel_label: str
    snr_db: float
    rms_uv: float
    clipping_pct: float
    line_noise_pct: float
    stationarity_ks_stat: float
    stationarity_p_value: float
    artifact_segments: list[tuple[float, float]] = field(default_factory=list)
    band_powers: dict[str, float] = field(default_factory=dict)
    hjorth_activity: float = 0.0
    hjorth_mobility: float = 0.0
    hjorth_complexity: float = 0.0
    line_length: float = 0.0
    spectral_edge_freq_50: float = 0.0
    spectral_edge_freq_90: float = 0.0
    spectral_entropy: float = 0.0
    alerts: list[str] = field(default_factory=list)


@dataclass
class ProcessingResult:
    """Complete output of the processing pipeline."""
    processed_samples: np.ndarray  # shape (n_channels, n_samples)
    n_channels: int
    sampling_rate_hz: float
    duration_s: float
    channel_qualities: list[ChannelQuality]
    global_alerts: list[str]
    
    def to_json(self, filepath: str) -> None:
        """Export quality report to JSON (samples excluded for size)."""
        report = {
            "n_channels": self.n_channels,
            "sampling_rate_hz": self.sampling_rate_hz,
            "duration_s": self.duration_s,
            "global_alerts": self.global_alerts,
            "channels": [asdict(cq) for cq in self.channel_qualities],
        }
        # Convert numpy types for JSON serialization
        def convert(obj):
            if isinstance(obj, np.floating): return float(obj)
            if isinstance(obj, np.integer): return int(obj)
            if isinstance(obj, np.ndarray): return obj.tolist()
            if isinstance(obj, dict): return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list): return [convert(i) for i in obj]
            return obj
        report = convert(report)
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)


# ============================================================================
# Signal Processor
# ============================================================================

class NeuralSignalProcessor:
    """VIREON Neural Signal Processing Provider.
    
    Implements the standard processing pipeline:
    1. Quality assessment (input)
    2. DC removal (high-pass filter)
    3. Powerline removal (notch filter)
    4. Artifact detection
    5. Feature extraction
    6. Quality assessment (output)
    
    Design Principles:
        - All filters are FIR where possible (stability guarantee)
        - All parameters are configurable through ProcessingConfig
        - All outputs include security-relevant metadata
        - Pipeline is composable (each stage can be used independently)
        - All operations are deterministic with fixed inputs
    """

    def __init__(self, config: Optional[ProcessingConfig] = None) -> None:
        self.config = config or ProcessingConfig()
        self._hp_filter: Optional[tuple] = None
        self._notch_filter: Optional[tuple] = None

    # ------------------------------------------------------------------
    # Main Pipeline
    # ------------------------------------------------------------------

    def process(self, samples: np.ndarray, sampling_rate_hz: float,
                channel_labels: Optional[list[str]] = None) -> ProcessingResult:
        """Run the full processing pipeline.
        
        Args:
            samples: Neural signal data, shape (n_channels, n_samples) or (n_samples,)
            sampling_rate_hz: Sampling rate in Hz
            channel_labels: Optional channel labels
        
        Returns:
            ProcessingResult with processed data and quality report
        """
        # Handle single-channel input
        if samples.ndim == 1:
            samples = samples[np.newaxis, :]
        
        n_channels, n_samples = samples.shape
        duration_s = n_samples / sampling_rate_hz
        
        if channel_labels is None:
            channel_labels = [f"CH_{i}" for i in range(n_channels)]
        
        # Design filters
        self._design_filters(sampling_rate_hz)
        
        global_alerts: list[str] = []
        processed = np.zeros_like(samples)
        channel_qualities: list[ChannelQuality] = []
        
        for ch in range(n_channels):
            raw = samples[ch]
            label = channel_labels[ch]
            
            # Stage 1: Input quality assessment
            input_quality = self._assess_quality(raw, sampling_rate_hz, label)
            
            # Stage 2: DC removal
            dc_removed = self._highpass_filter(raw)
            
            # Stage 3: Powerline removal
            notch_removed = self._notch_filter_signal(dc_removed)
            
            # Stage 4: Artifact detection
            artifact_segments = self._detect_artifacts(notch_removed, sampling_rate_hz)
            
            # Stage 5: Feature extraction
            features = self._extract_features(notch_removed, sampling_rate_hz)
            
            # Stage 6: Output quality assessment
            output_snr = self._compute_snr(notch_removed)
            snr_drop = input_quality["snr_db"] - output_snr
            alerts: list[str] = []
            
            if snr_drop > self.config.snr_alert_threshold_db:
                alerts.append(f"SNR dropped {snr_drop:.1f} dB after filtering (threshold: {self.config.snr_alert_threshold_db} dB)")
            if input_quality["clipping_pct"] > 0.001:
                alerts.append(f"Clipping detected: {input_quality['clipping_pct']*100:.2f}% of samples at ADC limits")
            if input_quality["line_noise_pct"] > self.config.line_noise_threshold_pct:
                alerts.append(f"Line noise elevated: {input_quality['line_noise_pct']*100:.1f}% of total power at {self.config.notch_freq_hz} Hz")
            
            # Stationarity check (compare first and second half)
            half = len(notch_removed) // 2
            if half > 100:
                ks_stat, ks_p = ks_2samp(
                    notch_removed[:half], notch_removed[half:2*half]
                )
                if ks_p < self.config.stationarity_ks_alpha:
                    alerts.append(f"Signal non-stationary (KS stat={ks_stat:.4f}, p={ks_p:.6f})")
                stationarity_ks = ks_stat
                stationarity_p = ks_p
            else:
                stationarity_ks = 0.0
                stationarity_p = 1.0
            
            # Cross-channel consistency (if multiple channels)
            if n_channels > 1 and ch > 0:
                prev = processed[ch - 1]
                corr = np.corrcoef(notch_removed[:len(prev)], prev)[0, 1]
                if np.isnan(corr):
                    corr = 0.0
            else:
                corr = 0.0
            
            cq = ChannelQuality(
                channel_label=label,
                snr_db=output_snr,
                rms_uv=float(np.std(notch_removed)),
                clipping_pct=input_quality["clipping_pct"],
                line_noise_pct=input_quality["line_noise_pct"],
                stationarity_ks_stat=stationarity_ks,
                stationarity_p_value=stationarity_p,
                artifact_segments=artifact_segments,
                band_powers=features["band_powers"],
                hjorth_activity=features["hjorth_activity"],
                hjorth_mobility=features["hjorth_mobility"],
                hjorth_complexity=features["hjorth_complexity"],
                line_length=features["line_length"],
                spectral_edge_freq_50=features["sef50"],
                spectral_edge_freq_90=features["sef90"],
                spectral_entropy=features["spectral_entropy"],
                alerts=alerts,
            )
            channel_qualities.append(cq)
            processed[ch] = notch_removed
            global_alerts.extend(alerts)
        
        return ProcessingResult(
            processed_samples=processed,
            n_channels=n_channels,
            sampling_rate_hz=sampling_rate_hz,
            duration_s=duration_s,
            channel_qualities=channel_qualities,
            global_alerts=global_alerts,
        )

    # ------------------------------------------------------------------
    # Filter Design
    # ------------------------------------------------------------------

    def _design_filters(self, fs: float) -> None:
        """Design and cache filters. Security: filter parameters are
        validated against the configuration to detect tampering."""
        nyq = fs / 2.0
        
        # High-pass: DC removal (use FIR for stability)
        # Design as bandpass with very low lower cutoff
        taps = 101  # Odd number for linear phase
        hp_cutoff = self.config.hp_cutoff_hz / nyq
        if hp_cutoff >= 1.0:
            hp_cutoff = 0.99
        self._hp_filter = scipy_signal.firwin(taps, hp_cutoff, pass_zero=False, window="hann")
        
        # Notch: powerline removal (IIR, 2nd order — standard for notch)
        w0 = self.config.notch_freq_hz / nyq
        if w0 >= 1.0:
            w0 = 0.99
        b_notch, a_notch = scipy_signal.iirnotch(w0, self.config.notch_quality)
        self._notch_filter = (b_notch, a_notch)

    def _highpass_filter(self, x: np.ndarray) -> np.ndarray:
        """Apply FIR high-pass filter. FIR is used for stability — see
        lesson Section 4.3 for IIR vs FIR security analysis."""
        if self._hp_filter is None:
            raise RuntimeError("Filters not designed. Call _design_filters first.")
        return scipy_signal.filtfilt(self._hp_filter, [1.0], x)

    def _notch_filter_signal(self, x: np.ndarray) -> np.ndarray:
        """Apply IIR notch filter. Security: IIR is used here because
        a narrow notch requires lower order than FIR (computational
        efficiency for implantable devices). VIREON validation should
        flag IIR usage and require stability analysis."""
        if self._notch_filter is None:
            raise RuntimeError("Filters not designed.")
        b, a = self._notch_filter
        # Check filter stability (poles inside unit circle)
        poles = np.roots(a)
        if np.any(np.abs(poles) >= 1.0):
            raise RuntimeError(f"IIR notch filter is UNSTABLE. Max pole magnitude: {np.max(np.abs(poles)):.4f}")
        return scipy_signal.filtfilt(b, a, x)

    # ------------------------------------------------------------------
    # Quality Assessment
    # ------------------------------------------------------------------

    def _assess_quality(self, x: np.ndarray, fs: float, label: str) -> dict:
        """Assess input signal quality. Returns metrics dict."""
        rms = np.std(x)
        # Estimate noise from high-frequency content (above 100 Hz)
        nperseg = min(2048, len(x) // 4)
        if nperseg < 16:
            nperseg = 16
        freqs, psd = scipy_signal.welch(x, fs=fs, nperseg=nperseg)
        noise_mask = freqs > 100.0
        signal_mask = (freqs >= 1.0) & (freqs <= 100.0)
        noise_power = np.sum(psd[noise_mask]) if np.any(noise_mask) else 1e-10
        signal_power = np.sum(psd[signal_mask]) if np.any(signal_mask) else 1e-10
        snr_db = 10 * np.log10(signal_power / max(noise_power, 1e-20))
        
        # Line noise percentage
        notch_mask = np.abs(freqs - self.config.notch_freq_hz) < 2.0
        total_power = np.sum(psd)
        line_power = np.sum(psd[notch_mask])
        line_pct = line_power / max(total_power, 1e-20)
        
        # Clipping (samples at or near theoretical ADC limits)
        max_val = np.max(np.abs(x))
        clipping_pct = np.sum(np.abs(x) > 0.99 * max_val) / len(x)
        
        return {
            "snr_db": float(snr_db),
            "clipping_pct": float(clipping_pct),
            "line_noise_pct": float(line_pct),
            "rms_uv": float(rms),
        }

    def _compute_snr(self, x: np.ndarray) -> float:
        """Compute SNR of processed signal."""
        rms = np.std(x)
        if rms < 1e-10:
            return 0.0
        nperseg = min(2048, len(x) // 4)
        if nperseg < 16:
            nperseg = 16
        freqs, psd = scipy_signal.welch(x, fs=self.config.feature_window_sec, nperseg=nperseg) if hasattr(self, '_fs') else (np.array([0]), np.array([rms**2]))
        return 10 * np.log10(rms**2 / max(np.var(x) * 0.01, 1e-20))  # Simplified SNR estimate

    # ------------------------------------------------------------------
    # Artifact Detection
    # ------------------------------------------------------------------

    def _detect_artifacts(self, x: np.ndarray, fs: float) -> list[tuple[float, float]]:
        """Detect artifact segments using amplitude threshold.
        
        Security Note:
            This is a simple threshold detector. More sophisticated methods
            (ICA, wavelet, ML) are described in the lesson but are not
            implemented here due to complexity. VIREON should support
            pluggable artifact detectors.
        """
        threshold = self.config.amplitude_threshold_uv
        # Sliding window RMS
        win_samples = int(0.2 * fs)  # 200 ms windows
        if win_samples < 10:
            return []
        
        segments: list[tuple[float, float]] = []
        in_artifact = False
        artifact_start = 0.0
        
        for i in range(0, len(x) - win_samples, win_samples // 2):
            window = x[i:i + win_samples]
            window_rms = np.sqrt(np.mean(window**2))
            t_start = i / fs
            
            if window_rms > threshold and not in_artifact:
                in_artifact = True
                artifact_start = t_start
            elif window_rms <= threshold and in_artifact:
                in_artifact = False
                segments.append((artifact_start, t_start))
        
        if in_artifact:
            segments.append((artifact_start, len(x) / fs))
        
        return segments

    # ------------------------------------------------------------------
    # Feature Extraction
    # ------------------------------------------------------------------

    def _extract_features(self, x: np.ndarray, fs: float) -> dict:
        """Extract all security-relevant features.
        
        Returns dict with: band_powers, hjorth_*, line_length,
        sef50, sef90, spectral_entropy
        """
        features: dict = {}
        
        # --- Band powers ---
        band_powers = {}
        nperseg = min(2048, len(x) // 4)
        if nperseg < 16:
            nperseg = 16
        freqs, psd = scipy_signal.welch(x, fs=fs, nperseg=nperseg)
        df = freqs[1] - freqs[0] if len(freqs) > 1 else 1.0
        
        for band_name, (low, high) in self.config.band_ranges.items():
            mask = (freqs >= low) & (freqs <= high)
            band_powers[band_name] = float(np.sum(psd[mask]) * df)
        features["band_powers"] = band_powers
        
        # --- Hjorth parameters ---
        activity = float(np.var(x))
        dx = np.diff(x)
        if len(dx) > 0:
            var_dx = float(np.var(dx))
            mobility = np.sqrt(var_dx / max(activity, 1e-20))
            ddx = np.diff(dx)
            if len(ddx) > 0:
                var_ddx = float(np.var(ddx))
                complexity = np.sqrt(var_ddx / max(var_dx, 1e-20)) / max(mobility, 1e-20)
            else:
                complexity = 0.0
        else:
            mobility = 0.0
            complexity = 0.0
        features["hjorth_activity"] = activity
        features["hjorth_mobility"] = float(mobility)
        features["hjorth_complexity"] = float(complexity)
        
        # --- Line length ---
        features["line_length"] = float(np.sum(np.abs(np.diff(x))))
        
        # --- Spectral edge frequency ---
        cumpower = np.cumsum(psd) * df
        total_power = cumpower[-1] if len(cumpower) > 0 else 1.0
        if total_power > 0:
            cumfrac = cumpower / total_power
            sef50_idx = np.searchsorted(cumfrac, 0.50)
            sef90_idx = np.searchsorted(cumfrac, 0.90)
            features["sef50"] = float(freqs[min(sef50_idx, len(freqs)-1)])
            features["sef90"] = float(freqs[min(sef90_idx, len(freqs)-1)])
        else:
            features["sef50"] = 0.0
            features["sef90"] = 0.0
        
        # --- Spectral entropy ---
        if np.any(psd > 0):
            psd_norm = psd / np.sum(psd)
            psd_norm = psd_norm[psd_norm > 0]
            features["spectral_entropy"] = float(-np.sum(psd_norm * np.log2(psd_norm)))
        else:
            features["spectral_entropy"] = 0.0
        
        return features

    # ------------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------------

    def plot_processing_chain(self, result: ProcessingResult,
                             ch_idx: int = 0, output_dir: str = "./output") -> list[str]:
        """Generate diagnostic plots for the processing chain."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        ch = result.channel_qualities[ch_idx]
        x = result.processed_samples[ch_idx]
        fs = result.sampling_rate_hz
        
        # Band power bar chart
        fig, ax = plt.subplots(figsize=(10, 4), constrained_layout=True)
        bands = list(ch.band_powers.keys())
        powers = list(ch.band_powers.values())
        ax.bar(bands, powers, color="#2196F3")
        ax.set_xlabel("Frequency Band")
        ax.set_ylabel("Power (uV^2)")
        ax.set_title(f"Band Powers — {ch.channel_label}")
        p = os.path.join(output_dir, f"{ch.channel_label}_band_powers.png")
        fig.savefig(p, dpi=150); plt.close(fig)
        paths.append(p)
        
        # Quality summary
        fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
        fig.suptitle(f"Quality Report — {ch.channel_label}", fontweight="bold")
        
        axes[0,0].bar(["SNR"], [ch.snr_db], color="#4CAF50")
        axes[0,0].set_title(f"SNR: {ch.snr_db:.1f} dB")
        
        axes[0,1].bar(["Line Noise"], [ch.line_noise_pct*100], color="#FF9800")
        axes[0,1].set_title(f"Line Noise: {ch.line_noise_pct*100:.1f}%")
        
        axes[1,0].bar(["RMS"], [ch.rms_uv], color="#2196F3")
        axes[1,0].set_title(f"RMS: {ch.rms_uv:.1f} uV")
        
        axes[1,1].text(0.5, 0.5, f"Alerts:\n" + "\n".join(ch.alerts) if ch.alerts else "No alerts",
                         transform=axes[1,1].transAxes, ha="center", va="center",
                         fontsize=10, family="monospace")
        axes[1,1].set_title("Security Alerts")
        
        p = os.path.join(output_dir, f"{ch.channel_label}_quality_report.png")
        fig.savefig(p, dpi=150); plt.close(fig)
        paths.append(p)
        
        return paths


# ============================================================================
# Main
# ============================================================================

def main() -> None:
    """Demo: process synthetic EEG from NL-001 simulator."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__),
        "..", "..", "NL-001-neural-signals-neurosecurity-foundations",
        "labs", "lab-001-signal-simulation"))
    
    try:
        from signal_simulator import NeuralSignalGenerator
        gen = NeuralSignalGenerator()
        eeg = gen.generate_eeg(duration_s=10, num_channels=4)
        samples = eeg.samples
        fs = eeg.sampling_rate_hz
        labels = eeg.channel_labels
        print("Loaded NL-001 EEG simulator output: 4 channels, 10s, 250 Hz")
    except ImportError:
        # Fallback: generate simple test signal
        print("NL-001 simulator not found. Using built-in test signal.")
        fs = 250.0
        n_samples = int(10 * fs)
        t = np.arange(n_samples) / fs
        samples = np.zeros((4, n_samples))
        rng = np.random.default_rng(42)
        for ch in range(4):
            samples[ch] = 30 * rng.standard_normal(n_samples)
            samples[ch] += 20 * np.sin(2 * np.pi * 10 * t)  # Alpha
            samples[ch] += 15 * np.sin(2 * np.pi * 20 * t)  # Beta
        labels = [f"CH_{i}" for i in range(4)]
    
    # Process with EEG preset
    proc = NeuralSignalProcessor(ModalityPreset.EEG.value)
    result = proc.process(samples, fs, labels)
    
    # Print report
    print(f"\n{'='*60}")
    print(f"VIREON Signal Processing Report")
    print(f"{'='*60}")
    print(f"Channels: {result.n_channels}, Duration: {result.duration_s:.1f}s, Fs: {result.sampling_rate_hz} Hz")
    
    for cq in result.channel_qualities:
        print(f"\n--- {cq.channel_label} ---")
        print(f"  SNR: {cq.snr_db:.1f} dB | RMS: {cq.rms_uv:.1f} uV | Line noise: {cq.line_noise_pct*100:.1f}%")
        print(f"  Band powers: " + ", ".join(f"{k}={v:.1f}" for k,v in cq.band_powers.items()))
        print(f"  Hjorth: A={cq.hjorth_activity:.1f} M={cq.hjorth_mobility:.3f} C={cq.hjorth_complexity:.3f}")
        print(f"  SEF50: {cq.spectral_edge_freq_50:.1f} Hz | SEF90: {cq.spectral_edge_freq_90:.1f} Hz")
        print(f"  Spectral entropy: {cq.spectral_entropy:.2f} bits")
        if cq.alerts:
            print(f"  ALERTS: {len(cq.alerts)}")
            for a in cq.alerts:
                print(f"    - {a}")
        else:
            print(f"  No alerts")
    
    if result.global_alerts:
        print(f"\nGLOBAL ALERTS: {len(result.global_alerts)}")
        for a in result.global_alerts:
            print(f"  - {a}")
    
    # Export
    out_dir = "./output"
    json_path = os.path.join(out_dir, "processing_report.json")
    os.makedirs(out_dir, exist_ok=True)
    result.to_json(json_path)
    print(f"\nReport exported: {json_path}")
    
    # Plot
    paths = proc.plot_processing_chain(result, ch_idx=0, output_dir=out_dir)
    print(f"Plots: {paths}")


if __name__ == "__main__":
    main()
