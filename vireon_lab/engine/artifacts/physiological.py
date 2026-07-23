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
from vireon_lab.engine.interfaces import IArtifactInjector

class EyeBlinkArtifact(IArtifactInjector):
    """
    Electrooculogram (EOG) eye blink artifact injector.
    Injects high-amplitude (>100 uV) bell-shaped transients primarily into frontal channels (F3, F4).
    """
    def __init__(self, blink_rate_hz: float = 0.35, amplitude_uv: float = 120.0):
        self.blink_rate_hz = blink_rate_hz
        self.amplitude_uv = amplitude_uv

    def inject(self, signals: np.ndarray, t_axis: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        num_channels, num_samples = signals.shape
        out_signals = signals.copy()
        
        # Periodic blink timing + jitter
        blink_centers = np.sin(2 * np.pi * self.blink_rate_hz * t_axis) > 0.98
        if np.any(blink_centers):
            pulse = self.amplitude_uv * np.exp(-((np.sin(2 * np.pi * self.blink_rate_hz * t_axis)) ** 2) / 0.005)
            # Frontal electrodes F3 (ch 0) and F4 (ch 1) pick up 100% of blink energy
            out_signals[0, :] += pulse
            out_signals[1, :] += pulse * 0.9
            # Parietal and occipital channels pick up reduced volume conduction (20%)
            out_signals[2:4, :] += pulse * 0.2
            
        return out_signals


class EMGBurstArtifact(IArtifactInjector):
    """
    Electromyogram (EMG) muscle artifact injector.
    Injects high-frequency (>30 Hz) burst energy into temporal and scalp electrodes.
    """
    def __init__(self, burst_probability: float = 0.05, amplitude_uv: float = 45.0):
        self.burst_probability = burst_probability
        self.amplitude_uv = amplitude_uv

    def inject(self, signals: np.ndarray, t_axis: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        num_channels, num_samples = signals.shape
        out_signals = signals.copy()
        
        if rng.random() < self.burst_probability:
            # High frequency 65Hz muscle activity burst
            emg_noise = rng.normal(0, self.amplitude_uv, size=num_samples) * np.sin(2 * np.pi * 65.0 * t_axis)
            target_ch = rng.choice(num_channels, size=min(4, num_channels), replace=False)
            for ch in target_ch:
                out_signals[ch, :] += emg_noise
                
        return out_signals


class ECGLeakageArtifact(IArtifactInjector):
    """
    Electrocardiogram (ECG) cardiac volume conduction artifact.
    Injects realistic QRS R-peak cardiac pulses at 1.1 Hz (66 BPM).
    """
    def __init__(self, hr_bpm: float = 66.0, amplitude_uv: float = 25.0):
        self.hr_hz = hr_bpm / 60.0
        self.amplitude_uv = amplitude_uv

    def inject(self, signals: np.ndarray, t_axis: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        num_channels, num_samples = signals.shape
        out_signals = signals.copy()
        
        # Sharp QRS R-peak complex pulse
        r_peaks = self.amplitude_uv * np.exp(-((t_axis % (1.0 / self.hr_hz) - 0.1) ** 2) / 0.0003)
        for ch in range(num_channels):
            out_signals[ch, :] += r_peaks * (0.8 + 0.4 * (ch / num_channels))
            
        return out_signals


class ElectrodeMotionArtifact(IArtifactInjector):
    """
    Electrode-skin impedance movement artifact.
    Simulates sudden baseline pop and slow exponential settling recovery.
    """
    def __init__(self, pop_probability: float = 0.02, pop_amplitude_uv: float = 250.0):
        self.pop_probability = pop_probability
        self.pop_amplitude_uv = pop_amplitude_uv

    def inject(self, signals: np.ndarray, t_axis: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        num_channels, num_samples = signals.shape
        out_signals = signals.copy()
        
        if rng.random() < self.pop_probability:
            target_ch = rng.integers(0, num_channels)
            pop_step = self.pop_amplitude_uv * np.exp(-np.linspace(0, 3.0, num_samples))
            out_signals[target_ch, :] += pop_step
            
        return out_signals
