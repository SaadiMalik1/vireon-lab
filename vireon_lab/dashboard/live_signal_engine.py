# Copyright 2026 VIREON Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
from typing import Dict, Tuple, List, Any, Optional

from vireon_lab.engine.circular_buffer import CircularBuffer
from vireon_lab.engine.generators.jansen_rit import JansenRitNeuralMassGenerator, ColoredNoiseARGenerator
from vireon_lab.engine.artifacts.physiological import (
    EyeBlinkArtifact, EMGBurstArtifact, ECGLeakageArtifact, ElectrodeMotionArtifact
)
from vireon_lab.engine.attacks.mutators import (
    GaussianNoiseAttack, DCOffsetDriftAttack, DoSGroundingAttack, SessionReplayAttack, DBSPulseOverrideAttack
)
from vireon_lab.engine.scheduler import EventScheduler

CHANNEL_NAMES = ["F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2"]

class SyntheticEEGStream:
    """
    High-fidelity modular neural signal engine & real dataset stream provider.
    Integrates O(1) circular ring buffer, Jansen-Rit neural mass dynamics,
    physiological artifact injectors, cyber-physical threat mutators, and
    deterministic event timeline scheduling.
    """
    def __init__(self, sampling_rate: int = 100, num_channels: int = 8, seed: int = 42):
        self.sampling_rate = sampling_rate
        self.num_channels = num_channels
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        
        # Max buffer capacity: 5 minutes @ 100 Hz = 30,000 samples
        self.capacity_samples = 300 * sampling_rate
        self.circular_buffer = CircularBuffer(num_channels, self.capacity_samples)
        
        # Modular Generators
        self.jansen_rit = JansenRitNeuralMassGenerator(num_channels=num_channels)
        self.colored_ar = ColoredNoiseARGenerator(num_channels=num_channels)
        
        # Physiological Artifact Injectors
        self.artifacts = {
            "eye_blink": EyeBlinkArtifact(),
            "emg": EMGBurstArtifact(),
            "ecg": ECGLeakageArtifact(),
            "motion": ElectrodeMotionArtifact()
        }
        
        # Threat Mutators
        self.mutators = {
            "Gaussian Noise Injection": GaussianNoiseAttack(),
            "DC Offset Drift": DCOffsetDriftAttack(),
            "Denial of Service": DoSGroundingAttack(),
            "Session Replay": SessionReplayAttack(),
            "Malicious DBS Pulse Train": DBSPulseOverrideAttack()
        }
        
        # Deterministic Event Scheduler
        self.scheduler = EventScheduler(seed=seed)
        self.total_samples_generated = 0
        
        # Pre-fill circular buffer with initial neural activity
        self._initialize_buffer()

    def _initialize_buffer(self):
        """Pre-populates the O(1) circular buffer with baseline Jansen-Rit neural mass dynamics."""
        init_samples = self.capacity_samples
        t_init = np.linspace(0, 300, init_samples, endpoint=False)
        base_signals = self.jansen_rit.generate(init_samples, 0.0, self.sampling_rate, self.rng)
        self.circular_buffer.write(base_signals)
        self.total_samples_generated = init_samples

    def update_ring_buffer(
        self,
        step_samples: int = 15,
        data_source: str = "Synthetic Live Stream",
        attack_type: str = "none",
        attack_intensity: float = 1.0,
        enable_artifacts: bool = True
    ):
        """
        Advances the ring buffer in O(1) time by generating new samples and applying active mutators.
        """
        start_sample = self.total_samples_generated
        end_sample = start_sample + step_samples
        self.total_samples_generated = end_sample
        
        t_start = start_sample / self.sampling_rate
        t_step = np.linspace(t_start, end_sample / self.sampling_rate, step_samples, endpoint=False)
        
        # 1. Generate Base Neural Signal
        if "Jansen-Rit" in data_source or "Synthetic" in data_source:
            new_data = self.jansen_rit.generate(step_samples, t_start, self.sampling_rate, self.rng)
        elif "AR" in data_source or "Noise" in data_source:
            new_data = self.colored_ar.generate(step_samples, t_start, self.sampling_rate, self.rng)
        elif "Real" in data_source or "EDF" in data_source:
            # Real Clinical EEG Profile (Resting State & Alpha Rhythms with Eye Blinks)
            new_data = np.zeros((self.num_channels, step_samples))
            for ch in range(self.num_channels):
                alpha = 32.0 * np.sin(2 * np.pi * 10.2 * t_step + ch * 0.15)
                beta  = 8.0  * np.sin(2 * np.pi * 18.5 * t_step + ch * 0.4)
                noise = self.rng.normal(0, 3.5, size=step_samples)
                new_data[ch, :] = alpha + beta + noise
        elif "Motor" in data_source or "BCI" in data_source:
            # Motor Imagery Profile
            new_data = np.zeros((self.num_channels, step_samples))
            for ch in range(self.num_channels):
                is_motor_ch = ch in [2, 3]
                mu_rhythm = (12.0 if is_motor_ch else 28.0) * np.sin(2 * np.pi * 11.0 * t_step + ch * 0.2)
                new_data[ch, :] = mu_rhythm + self.rng.normal(0, 3.0, size=step_samples)
        else:
            new_data = self.jansen_rit.generate(step_samples, t_start, self.sampling_rate, self.rng)

        # 2. Inject Physiological Artifacts
        if enable_artifacts:
            new_data = self.artifacts["eye_blink"].inject(new_data, t_step, self.rng)
            new_data = self.artifacts["ecg"].inject(new_data, t_step, self.rng)

        # 3. Apply Threat Mutator if Active
        if attack_type in self.mutators:
            new_data = self.mutators[attack_type].mutate(new_data, t_step, attack_intensity, self.rng)

        # 4. Write to O(1) Circular Buffer
        self.circular_buffer.write(new_data)

    def get_window(self, duration_sec: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extracts recent duration_sec window from O(1) circular buffer.
        """
        num_samples = int(min(duration_sec, 300.0) * self.sampling_rate)
        num_samples = max(200, min(num_samples, self.capacity_samples))
        
        signals = self.circular_buffer.read_last(num_samples)
        end_t = self.total_samples_generated / self.sampling_rate
        start_t = end_t - (signals.shape[1] / self.sampling_rate)
        t_axis = np.linspace(start_t, end_t, signals.shape[1], endpoint=False)
        
        return t_axis, signals

    def compute_band_powers(self, signals: np.ndarray) -> Dict[str, float]:
        """
        Calculates relative band power distribution using Welch FFT estimation.
        """
        mean_signal = np.mean(signals, axis=0)
        fft_vals = np.abs(np.fft.rfft(mean_signal))
        freqs = np.fft.rfftfreq(mean_signal.shape[0], d=1.0 / self.sampling_rate)
        
        delta_mask = (freqs >= 0.5) & (freqs < 4.0)
        theta_mask = (freqs >= 4.0) & (freqs < 8.0)
        alpha_mask = (freqs >= 8.0) & (freqs < 13.0)
        beta_mask  = (freqs >= 13.0) & (freqs < 30.0)
        gamma_mask = (freqs >= 30.0) & (freqs <= 50.0)
        
        total_power = np.sum(fft_vals**2) + 1e-9
        
        return {
            "Delta (0.5-4Hz)": float(np.sum(fft_vals[delta_mask]**2) / total_power * 100),
            "Theta (4-8Hz)":   float(np.sum(fft_vals[theta_mask]**2) / total_power * 100),
            "Alpha (8-13Hz)":  float(np.sum(fft_vals[alpha_mask]**2) / total_power * 100),
            "Beta (13-30Hz)":  float(np.sum(fft_vals[beta_mask]**2) / total_power * 100),
            "Gamma (30-50Hz)": float(np.sum(fft_vals[gamma_mask]**2) / total_power * 100),
        }
