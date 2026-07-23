"""
VIREON-LABS NL-001 Lab 001: Neural Signal Simulator with Security Annotations
=========================================================================

This module simulates the four primary neural signal modalities (EEG, ECoG,
LFP, spike trains) with physiologically grounded parameters. Each signal
generator includes security annotations that describe the security relevance
of the generated signal properties.

Learning Objectives:
    1. Understand the time-domain and frequency-domain properties of each
       neural signal modality
    2. Generate physiologically plausible synthetic neural signals
    3. Understand how signal properties affect security (bandwidth constrains
       crypto overhead, amplitude affects injection feasibility, etc.)
    4. Produce signals suitable for VIREON digital twin inputs

Required Software:
    - Python 3.9+
    - numpy, scipy, matplotlib

Required Hardware: None

Estimated Completion Time: 2-3 hours

Difficulty: Intermediate

Expected Outputs:
    - Time-domain plots for each modality
    - Power spectral density plots for each modality
    - A security annotation report

Validation Criteria:
    - Generated EEG PSD matches published 1/f^alpha characteristic
    - Generated spike trains have realistic inter-spike interval distributions
    - All security annotations are complete and accurate

Usage:
    python signal_simulator.py --modality all --duration 10 --output_dir ./output
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal as scipy_signal


# ============================================================================
# Type Definitions
# ============================================================================

class SignalModality(Enum):
    """Neural signal modality types with security-relevant metadata."""
    EEG = "eeg"
    ECOG = "ecog"
    LFP = "lfp"
    SPIKE = "spike"


@dataclass
class SecurityAnnotation:
    """Security-relevant metadata for a generated signal."""
    modality: str
    bandwidth_hz: tuple[float, float]
    amplitude_range_uv: tuple[float, float]
    sampling_rate_hz: float
    data_rate_bps: float  # bits per second for raw samples
    injection_feasibility: str  # qualitative assessment
    exfiltration_impact: str  # qualitative assessment
    cryptographic_overhead_budget: str  # how much crypto overhead is tolerable
    trust_boundaries_crossed: list[str]
    known_attack_vectors: list[str]
    notes: str


@dataclass
class NeuralSignal:
    """Container for a generated neural signal with metadata."""
    modality: SignalModality
    samples: np.ndarray  # voltage in microvolts (uV)
    timestamps: np.ndarray  # time in seconds
    sampling_rate_hz: float
    num_channels: int
    channel_labels: list[str]
    security_annotation: SecurityAnnotation
    generation_params: dict = field(default_factory=dict)


# ============================================================================
# Signal Generators
# ============================================================================

class NeuralSignalGenerator:
    """
    Generates synthetic neural signals with physiologically grounded parameters.
    
    Design Rationale:
        Each generator produces signals whose statistical properties match
        published neurophysiological data. This is essential for VIREON
        because validation experiments require signals with known ground truth.
        Synthetic signals provide this ground truth.
    
    Security Rationale:
        The signal properties generated here directly determine the security
        characteristics of the system that processes them. For example:
        - A 500 Hz EEG signal requires ~8 kbps per channel (16-bit, 250 S/s)
        - A 6 kHz spike signal requires ~192 kbps per channel (16-bit, 12 kS/s)
        - Higher data rates leave less bandwidth for cryptographic overhead
        - Higher amplitudes require attackers to inject stronger EMI signals
    """

    def __init__(self, rng_seed: int = 42) -> None:
        self.rng = np.random.default_rng(rng_seed)

    def generate_eeg(
        self,
        duration_s: float = 10.0,
        num_channels: int = 8,
        sampling_rate_hz: float = 250.0,
        include_artifacts: bool = True,
    ) -> NeuralSignal:
        """Generate synthetic scalp EEG.
        
        Physiological Basis:
            Scalp EEG primarily reflects synchronized postsynaptic potentials
            in cortical pyramidal neurons. The signal is band-limited by
            volume conduction through the skull.
        
        Signal Model:
            1. Background: 1/f (pink) noise approximating the EEG PSD
            2. Rhythmic components: delta, theta, alpha, beta, gamma
            3. Artifacts (optional): eye blink, muscle
        
        Security Relevance:
            EEG is the most widely deployed neural recording modality in
            consumer devices (Muse, Emotiv, OpenBCI). Consumer deployment
            creates a large, accessible attack surface. EEG data contains
            biometric information (individual identification >95% accuracy),
            cognitive state information, and private information.
        """
        n_samples = int(duration_s * sampling_rate_hz)
        timestamps = np.arange(n_samples) / sampling_rate_hz
        freqs = np.fft.rfftfreq(n_samples, 1.0 / sampling_rate_hz)

        # 1/f^alpha background (alpha ~ 1.5 for resting state EEG)
        alpha = 1.5
        psd = np.zeros_like(freqs)
        psd[1:] = 1.0 / (freqs[1:] ** alpha)
        psd[freqs < 0.5] = 0
        psd[freqs > 100.0] = 0
        amplitudes = np.sqrt(psd)
        phases = self.rng.uniform(0, 2 * np.pi, len(freqs))
        spectrum = amplitudes * np.exp(1j * phases)
        background = np.fft.irfft(spectrum, n=n_samples)
        background = background * (30.0 / np.std(background))  # 30 uV RMS

        # Canonical rhythms
        rhythms = {
            "alpha": {"freq": 10.0, "rel_power": 0.3},
            "beta": {"freq": 20.0, "rel_power": 0.15},
            "theta": {"freq": 6.0, "rel_power": 0.1},
            "delta": {"freq": 2.0, "rel_power": 0.05},
        }
        rhythmic = np.zeros(n_samples)
        for name, params in rhythms.items():
            jitter = self.rng.normal(0, 0.1, n_samples)
            osc = np.sin(2 * np.pi * params["freq"] * timestamps + np.cumsum(jitter) / sampling_rate_hz * 2 * np.pi)
            rhythmic += params["rel_power"] * osc
        rhythmic = rhythmic * (20.0 / np.std(rhythmic))
        eeg = background + rhythmic

        # Multi-channel with spatial correlation
        channel_labels = ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4"][:num_channels]
        positions = {
            "Fp1": (-3, 8), "Fp2": (3, 8), "F3": (-4, 2), "F4": (4, 2),
            "C3": (-4, -2), "C4": (4, -2), "P3": (-3, -6), "P4": (3, -6),
        }
        pos = np.array([positions.get(ch, (0, 0)) for ch in channel_labels])
        distances = np.linalg.norm(pos[:, None] - pos[None, :], axis=2)
        correlation = np.exp(-distances / 5.0)
        L = np.linalg.cholesky(correlation)
        independent = self.rng.standard_normal((n_samples, num_channels))
        correlated_noise = independent @ L.T
        correlated_noise = correlated_noise / np.std(correlated_noise) * np.std(background) * 0.5

        channels = np.zeros((num_channels, n_samples))
        for ch in range(num_channels):
            channels[ch] = eeg + correlated_noise[:, ch]

        if include_artifacts:
            channels = self._add_eeg_artifacts(channels, timestamps, sampling_rate_hz, channel_labels)

        security = SecurityAnnotation(
            modality="EEG",
            bandwidth_hz=(0.5, 100.0),
            amplitude_range_uv=(10.0, 100.0),
            sampling_rate_hz=sampling_rate_hz,
            data_rate_bps=sampling_rate_hz * 16,
            injection_feasibility="HIGH - Low amplitude (10-100 uV) means attackers need only inject ~50-500 uV EMI. Scalp accessibility lowers physical barrier.",
            exfiltration_impact="MEDIUM-HIGH - EEG contains biometric identifiers, cognitive state markers, private information.",
            cryptographic_overhead_budget="MODERATE - Low per-channel data rate (~4 kbps at 250 S/s, 16-bit) allows room for encryption.",
            trust_boundaries_crossed=[
                "Electrode-scalp interface (physical)",
                "Amplifier-ADC (analog-to-digital)",
                "Device-BLE transmitter (digital-to-RF)",
                "BLE-receiver-application (RF-to-digital)",
                "Application-cloud (digital-to-network)",
            ],
            known_attack_vectors=[
                "EMI injection at electrode site",
                "BLE packet interception",
                "Replay of recorded EEG sessions",
                "Adversarial examples against BCI classifiers",
                "EEG side-channel reveals typed keys (Martinovic 2012)",
                "Model inversion to extract training data",
            ],
            notes="EEG is the entry point for most consumer neurotechnology attacks.",
        )

        return NeuralSignal(
            modality=SignalModality.EEG,
            samples=channels,
            timestamps=timestamps,
            sampling_rate_hz=sampling_rate_hz,
            num_channels=num_channels,
            channel_labels=channel_labels,
            security_annotation=security,
            generation_params={
                "duration_s": duration_s, "num_channels": num_channels,
                "sampling_rate_hz": sampling_rate_hz, "include_artifacts": include_artifacts,
                "psd_exponent": alpha,
            },
        )

    def _add_eeg_artifacts(
        self, channels: np.ndarray, timestamps: np.ndarray,
        fs: float, labels: list[str],
    ) -> np.ndarray:
        """Add eye blink artifacts to anterior EEG channels."""
        n_samples = len(timestamps)
        artifacted = channels.copy()
        n_blinks = self.rng.integers(2, 4)
        for _ in range(n_blinks):
            center = self.rng.integers(0, n_samples)
            width = int(0.3 * fs)
            t = np.arange(-width, width) / fs
            blink = 100.0 * np.exp(-((t + 0.05) ** 2) / (2 * 0.05 ** 2))
            blink[t < -0.05] = 0
            for ch_idx, label in enumerate(labels):
                if label.startswith("Fp"):
                    start = max(0, center - width)
                    end = min(n_samples, center + width)
                    artifacted[ch_idx, start:end] += blink[:end - start]
        return artifacted

    def generate_ecog(
        self, duration_s: float = 10.0, num_channels: int = 8,
        sampling_rate_hz: float = 500.0,
    ) -> NeuralSignal:
        """Generate synthetic ECoG signals.
        
        Physiological Basis:
            ECoG bypasses the skull, giving higher amplitude (50-500 uV),
            wider bandwidth (up to 500 Hz), and better spatial resolution.
        """
        n_samples = int(duration_s * sampling_rate_hz)
        timestamps = np.arange(n_samples) / sampling_rate_hz
        freqs = np.fft.rfftfreq(n_samples, 1.0 / sampling_rate_hz)

        alpha = 1.0  # Flatter than EEG (less skull filtering)
        psd = np.zeros_like(freqs)
        psd[1:] = 1.0 / (freqs[1:] ** alpha)
        psd[freqs < 1.0] = 0
        psd[freqs > 500.0] = 0
        amplitudes = np.sqrt(psd)
        phases = self.rng.uniform(0, 2 * np.pi, len(freqs))
        spectrum = amplitudes * np.exp(1j * phases)
        background = np.fft.irfft(spectrum, n=n_samples)
        background = background * (100.0 / np.std(background))

        # High-gamma (50-200 Hz) augmentation prominent in ECoG
        hg = np.zeros(n_samples)
        for f in range(60, 201, 20):
            hg += 0.3 * np.sin(2 * np.pi * f * timestamps + self.rng.uniform(0, 2 * np.pi))
        hg *= (30.0 / np.std(hg))
        ecog = background + hg

        channels = np.zeros((num_channels, n_samples))
        positions = np.array([[i * 10, j * 10] for i in range(4) for j in range(2)])[:num_channels]
        distances = np.linalg.norm(positions[:, None] - positions[None, :], axis=2)
        correlation = np.exp(-distances / 10.0)
        L = np.linalg.cholesky(correlation)
        independent = self.rng.standard_normal((n_samples, num_channels))
        correlated = independent @ L.T * (np.std(background) * 0.3 / np.std(independent))
        for ch in range(num_channels):
            channels[ch] = ecog + correlated[:, ch]

        security = SecurityAnnotation(
            modality="ECoG",
            bandwidth_hz=(1.0, 500.0),
            amplitude_range_uv=(50.0, 500.0),
            sampling_rate_hz=sampling_rate_hz,
            data_rate_bps=sampling_rate_hz * 16,
            injection_feasibility="LOW - Implanted electrodes are physically protected behind scalp and skull.",
            exfiltration_impact="HIGH - Higher spatial/temporal resolution encodes detailed motor/sensory information.",
            cryptographic_overhead_budget="MODERATE-LOW - ~8 kbps/channel at 500 S/s, 16-bit.",
            trust_boundaries_crossed=[
                "Electrode-cortex interface (surgically implanted)",
                "Internal RF telemetry (implant to external)",
                "External receiver-clinical system (digital)",
            ],
            known_attack_vectors=[
                "Wireless telemetry interception",
                "Compromise of external receiver/programmer",
                "Firmware manipulation of implanted recorder",
                "Supply chain attack on implant",
            ],
            notes="ECoG's semi-invasive nature provides physical protection but external telemetry is the primary wireless attack surface.",
        )

        return NeuralSignal(
            modality=SignalModality.ECOG, samples=channels, timestamps=timestamps,
            sampling_rate_hz=sampling_rate_hz, num_channels=num_channels,
            channel_labels=[f"ECoG_{i}" for i in range(num_channels)],
            security_annotation=security,
            generation_params={"duration_s": duration_s, "num_channels": num_channels, "sampling_rate_hz": sampling_rate_hz},
        )

    def generate_lfp(
        self, duration_s: float = 10.0, num_channels: int = 4,
        sampling_rate_hz: float = 250.0, target_region: str = "STN",
    ) -> NeuralSignal:
        """Generate synthetic LFP from deep brain structures.
        
        CRITICAL SECURITY RELEVANCE:
            LFP drives therapeutic stimulation in closed-loop DBS systems.
            Injecting false LFP can manipulate the closed-loop controller
            to deliver incorrect stimulation — direct patient harm.
        """
        n_samples = int(duration_s * sampling_rate_hz)
        timestamps = np.arange(n_samples) / sampling_rate_hz
        freqs = np.fft.rfftfreq(n_samples, 1.0 / sampling_rate_hz)

        alpha = 1.2
        psd = np.zeros_like(freqs)
        psd[1:] = 1.0 / (freqs[1:] ** alpha)
        psd[freqs < 2.0] = 0
        psd[freqs > 100.0] = 0
        amplitudes = np.sqrt(psd)
        phases = self.rng.uniform(0, 2 * np.pi, len(freqs))
        spectrum = amplitudes * np.exp(1j * phases)
        background = np.fft.irfft(spectrum, n=n_samples)
        background = background * (200.0 / np.std(background))

        # Prominent beta peak (13-30 Hz) — the clinical biomarker for PD DBS
        beta_amplitude = 150.0 * (1.0 + 0.3 * np.sin(2 * np.pi * 0.1 * timestamps))
        beta_freq = 20.0 + 2.0 * np.sin(2 * np.pi * 0.05 * timestamps)
        beta_phase = np.cumsum(2 * np.pi * beta_freq) / sampling_rate_hz
        beta = beta_amplitude * np.sin(beta_phase)
        lfp = background + beta

        channels = np.zeros((num_channels, n_samples))
        # DBS leads: 4 contacts, 1.5 mm spacing
        positions = np.array([[0, i * 1.5] for i in range(num_channels)])
        distances = np.linalg.norm(positions[:, None] - positions[None, :], axis=2)
        correlation = np.exp(-distances / 2.0)
        L = np.linalg.cholesky(correlation)
        independent = self.rng.standard_normal((n_samples, num_channels))
        correlated = independent @ L.T * (np.std(background) * 0.2 / np.std(independent))
        for ch in range(num_channels):
            channels[ch] = lfp + correlated[:, ch]

        security = SecurityAnnotation(
            modality="LFP",
            bandwidth_hz=(2.0, 100.0),
            amplitude_range_uv=(100.0, 1000.0),
            sampling_rate_hz=sampling_rate_hz,
            data_rate_bps=sampling_rate_hz * 16,
            injection_feasibility="VERY LOW - Deep brain electrodes, stereotactic access required, heavy tissue attenuation.",
            exfiltration_impact="CRITICAL - In closed-loop DBS, LFP directly controls stimulation. False data = incorrect therapy.",
            cryptographic_overhead_budget="LOW - Latency budget <10 ms constrains time for crypto in feedback loop.",
            trust_boundaries_crossed=[
                "Electrode-brain tissue (deep, implanted)",
                "Lead-IPG connector (hermetically sealed)",
                "IPG AFE-ADC-DSP (firmware-controlled)",
                "IPG RF telemetry MICS band (PRIMARY ATTACK SURFACE)",
                "External programmer-clinical system (digital)",
            ],
            known_attack_vectors=[
                "MICS-band telemetry interception and manipulation",
                "Replay of LFP data to manipulate closed-loop controller",
                "Firmware compromise to alter LFP processing",
                "Beta-band injection to suppress or trigger stimulation inappropriately",
                "LFP feature extraction manipulation (change beta threshold)",
            ],
            notes="HIGHEST-PRIORITY MODALITY FOR VIREON VALIDATION. Closed-loop systems create an exploitable feedback loop.",
        )

        return NeuralSignal(
            modality=SignalModality.LFP, samples=channels, timestamps=timestamps,
            sampling_rate_hz=sampling_rate_hz, num_channels=num_channels,
            channel_labels=[f"Contact_{i}" for i in range(num_channels)],
            security_annotation=security,
            generation_params={"duration_s": duration_s, "num_channels": num_channels, "sampling_rate_hz": sampling_rate_hz, "target_region": target_region},
        )

    def generate_spike_trains(
        self, duration_s: float = 10.0, num_neurons: int = 5,
        mean_firing_rate_hz: float = 10.0, sampling_rate_hz: float = 30000.0,
    ) -> NeuralSignal:
        """Generate synthetic spike trains (single-unit activity).
        
        Security Relevance:
            Highest information density. Neuralink's 1024-channel system at
            20 kS/s = ~327 Mbps raw data rate. Enormous data exfiltration risk.
        """
        n_samples = int(duration_s * sampling_rate_hz)
        timestamps = np.arange(n_samples) / sampling_rate_hz
        channels = np.zeros((num_neurons, n_samples))
        spike_times_all: list[list[float]] = []

        for neuron in range(num_neurons):
            rate = mean_firing_rate_hz * self.rng.uniform(0.5, 1.5)
            refractory = 0.002
            spike_times: list[float] = []
            t = self.rng.uniform(0, refractory)
            while t < duration_s:
                spike_times.append(t)
                t += self.rng.exponential(1.0 / rate) + refractory
            spike_times_all.append(spike_times)

            # Biphasic spike waveform (~1 ms)
            sw = int(0.001 * sampling_rate_hz)
            t_spike = np.linspace(0, 0.001, sw, endpoint=False)
            waveform = np.zeros(sw)
            pos = t_spike < 0.0004
            neg = (t_spike >= 0.0004) & (t_spike < 0.0008)
            waveform[pos] = 300.0 * np.sin(np.pi * t_spike[pos] / 0.0004)
            waveform[neg] = -150.0 * np.sin(np.pi * (t_spike[neg] - 0.0004) / 0.0004)
            waveform *= self.rng.uniform(0.8, 1.2)

            for st in spike_times:
                idx = int(st * sampling_rate_hz)
                if idx + sw < n_samples:
                    noise = self.rng.normal(0, 5.0, sw)
                    channels[neuron, idx:idx + sw] = waveform + noise

        channels += self.rng.normal(0, 10.0, (num_neurons, n_samples))

        security = SecurityAnnotation(
            modality="Spike",
            bandwidth_hz=(300.0, 6000.0),
            amplitude_range_uv=(100.0, 1000.0),
            sampling_rate_hz=sampling_rate_hz,
            data_rate_bps=sampling_rate_hz * 16,
            injection_feasibility="NEGLIGIBLE - Microelectrodes in brain tissue. EMI injection at microelectrode scale impractical.",
            exfiltration_impact="CRITICAL - Highest information density. Neuralink 1024-ch at 20 kS/s ~327 Mbps raw.",
            cryptographic_overhead_budget="VERY LOW - Extreme data rate makes real-time encryption challenging.",
            trust_boundaries_crossed=[
                "Microelectrode-brain tissue (penetrating, implanted)",
                "Internal signal chain (hermetically sealed)",
                "Wireless telemetry (custom high-bandwidth)",
                "External decoder-BCI application (digital)",
            ],
            known_attack_vectors=[
                "High-bandwidth wireless link interception",
                "Decoder model inversion (extract motor intentions)",
                "Adversarial examples against neural decoders (Zhang 2019)",
                "Supply chain compromise of implant chip",
                "Firmware manipulation to exfiltrate raw spike data",
            ],
            notes="Greatest challenge for VIREON: data rate may exceed what can be encrypted with available power budgets in real-time.",
        )

        return NeuralSignal(
            modality=SignalModality.SPIKE, samples=channels, timestamps=timestamps,
            sampling_rate_hz=sampling_rate_hz, num_channels=num_neurons,
            channel_labels=[f"Neuron_{i}" for i in range(num_neurons)],
            security_annotation=security,
            generation_params={"duration_s": duration_s, "num_neurons": num_neurons, "mean_firing_rate_hz": mean_firing_rate_hz, "sampling_rate_hz": sampling_rate_hz},
        )


# ============================================================================
# Visualization
# ============================================================================

class SignalVisualizer:
    """Generates plots for neural signal analysis and VIREON benchmark output."""

    def __init__(self, output_dir: str = "./output") -> None:
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def plot_time_domain(self, ns: NeuralSignal, time_range_s: tuple[float, float] = (0.0, 2.0)) -> str:
        ch = 0
        mask = (ns.timestamps >= time_range_s[0]) & (ns.timestamps < time_range_s[1])
        t, y = ns.timestamps[mask], ns.samples[ch, mask]
        fig, ax = plt.subplots(figsize=(12, 4), constrained_layout=True)
        ax.plot(t, y, linewidth=0.5)
        ax.set_xlabel("Time (s)"); ax.set_ylabel("Amplitude (uV)")
        ax.set_title(f"{ns.modality.value.upper()} - Time Domain - {ns.channel_labels[ch]}")
        ax.grid(True, alpha=0.3)
        path = os.path.join(self.output_dir, f"{ns.modality.value}_time_domain.png")
        fig.savefig(path, dpi=150); plt.close(fig)
        return path

    def plot_psd(self, ns: NeuralSignal) -> str:
        fs = ns.sampling_rate_hz
        freqs, psd = scipy_signal.welch(ns.samples[0], fs=fs, nperseg=min(2048, len(ns.samples[0]) // 4))
        fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
        ax.semilogy(freqs, psd, linewidth=1)
        ax.set_xlabel("Frequency (Hz)"); ax.set_ylabel("PSD (uV^2/Hz)")
        ax.set_title(f"{ns.modality.value.upper()} - Power Spectral Density")
        ax.set_xlim(0, min(200, fs / 2)); ax.grid(True, alpha=0.3, which="both")
        path = os.path.join(self.output_dir, f"{ns.modality.value}_psd.png")
        fig.savefig(path, dpi=150); plt.close(fig)
        return path

    def plot_security_summary(self, ns: NeuralSignal) -> str:
        sa = ns.security_annotation
        fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
        fig.suptitle(f"{sa.modality} Security Summary", fontsize=14, fontweight="bold")
        bw = sa.bandwidth_hz
        axes[0].barh(["Lower", "Upper"], [bw[0], bw[1]], color=["#2196F3", "#F44336"])
        axes[0].set_xlabel("Frequency (Hz)"); axes[0].set_title("Bandwidth"); axes[0].set_xlim(0, 6000)
        axes[1].barh(["Raw"], [sa.data_rate_bps / 1000], color="#FF9800")
        axes[1].set_xlabel("Data Rate (kbps)"); axes[1].set_title("Per-Channel Data Rate")
        amp = sa.amplitude_range_uv
        axes[2].barh(["Min", "Max"], amp, color=["#4CAF50", "#9C27B0"])
        axes[2].set_xlabel("Amplitude (uV)"); axes[2].set_title("Amplitude Range")
        path = os.path.join(self.output_dir, f"{ns.modality.value}_security_summary.png")
        fig.savefig(path, dpi=150); plt.close(fig)
        return path


# ============================================================================
# Main
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="VIREON-LABS NL-001 Neural Signal Simulator")
    parser.add_argument("--modality", choices=["eeg", "ecog", "lfp", "spike", "all"], default="all")
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--output_dir", default="./output")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    gen = NeuralSignalGenerator(rng_seed=args.seed)
    viz = SignalVisualizer(output_dir=args.output_dir)
    modalities = {"eeg": gen.generate_eeg, "ecog": gen.generate_ecog, "lfp": gen.generate_lfp, "spike": gen.generate_spike_trains}
    selected = list(modalities.keys()) if args.modality == "all" else [args.modality]
    results = {}

    for mod_name in selected:
        print(f"\n{'='*60}\nGenerating {mod_name.upper()}...\n{'='*60}")
        if mod_name == "spike":
            ns = modalities[mod_name](duration_s=args.duration, num_neurons=5)
        else:
            ns = modalities[mod_name](duration_s=args.duration)
        results[mod_name] = ns
        print(f"  Channels: {ns.num_channels}")
        print(f"  Sampling Rate: {ns.sampling_rate_hz} Hz")
        print(f"  Data Rate: {ns.security_annotation.data_rate_bps / 1000:.1f} kbps/ch")
        print(f"  Injection: {ns.security_annotation.injection_feasibility.split(' - ')[0]}")
        print(f"  Exfil Impact: {ns.security_annotation.exfiltration_impact.split(' - ')[0]}")
        print(f"  Time domain: {viz.plot_time_domain(ns)}")
        print(f"  PSD: {viz.plot_psd(ns)}")
        print(f"  Security: {viz.plot_security_summary(ns)}")

    annotations = {m: {
        "modality": results[m].security_annotation.modality,
        "bandwidth_hz": list(results[m].security_annotation.bandwidth_hz),
        "amplitude_range_uv": list(results[m].security_annotation.amplitude_range_uv),
        "data_rate_bps": results[m].security_annotation.data_rate_bps,
        "injection": results[m].security_annotation.injection_feasibility,
        "exfiltration": results[m].security_annotation.exfiltration_impact,
        "trust_boundaries": results[m].security_annotation.trust_boundaries_crossed,
        "attack_vectors": results[m].security_annotation.known_attack_vectors,
    } for m in results}
    json_path = os.path.join(args.output_dir, "security_annotations.json")
    with open(json_path, "w") as f:
        json.dump(annotations, f, indent=2)
    print(f"\nSecurity annotations: {json_path}")

    print(f"\n{'='*60}\nCOMPARATIVE SECURITY SUMMARY\n{'='*60}")
    print(f"{'Modality':<8} {'BW (Hz)':<16} {'Amplitude':<18} {'Data Rate':<12} {'Injection':<12} {'Exfil'}")
    print("-" * 80)
    for m, ns in results.items():
        sa = ns.security_annotation
        print(f"{sa.modality:<8} {str(sa.bandwidth_hz):<16} {str(sa.amplitude_range_uv):<18} {sa.data_rate_bps/1000:.1f} kbps   {sa.injection_feasibility.split(' - ')[0]:<12} {sa.exfiltration_impact.split(' - ')[0]}")


if __name__ == "__main__":
    main()
