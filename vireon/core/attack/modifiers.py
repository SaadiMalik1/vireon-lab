import numpy as np
from typing import List, Dict, Optional
from vireon.core.twin import DigitalTwin

from .base import ISignalModifier

class NoiseInjectionAttack(ISignalModifier):
    def __init__(self, target_channels: List[int], noise_level_microvolts: float = 50.0):
        self.target_channels = target_channels
        self.noise_level = noise_level_microvolts

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        mutated_data = data.copy()
        for ch in self.target_channels:
            if ch in eeg_channels:
                # Add Gaussian noise
                noise = (rng if rng is not None else np.random).normal(0, self.noise_level, size=data.shape[1])
                mutated_data[ch, :] += noise
        return mutated_data


class SignalDriftAttack(ISignalModifier):
    def __init__(self, target_channels: List[int], drift_rate_uv_per_sec: float = 20.0):
        self.target_channels = target_channels
        self.drift_rate = drift_rate_uv_per_sec
        # Maintain drift offsets across calls
        self.offsets: Dict[int, float] = {ch: 0.0 for ch in target_channels}

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        mutated_data = data.copy()
        num_samples = data.shape[1]
        dt = num_samples / sample_rate

        for ch in self.target_channels:
            if ch in eeg_channels:
                start_offset = self.offsets.get(ch, 0.0)
                # Compute linear drift vector for this block
                drift_vector = np.linspace(start_offset, start_offset + self.drift_rate * dt, num_samples)
                mutated_data[ch, :] += drift_vector
                # Store final offset for the next chunk
                self.offsets[ch] = start_offset + self.drift_rate * dt
        return mutated_data


class ImpedanceSpikeAttack(ISignalModifier):
    def __init__(self, target_channels: List[int], spike_value_kohm: float = 150.0, powerline_noise_amplitude: float = 100.0):
        self.target_channels = target_channels
        self.spike_value = spike_value_kohm
        self.powerline_noise_amplitude = powerline_noise_amplitude
        self.time_counter = 0.0

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        mutated_data = data.copy()
        num_samples = data.shape[1]

        # Create a powerline interference (50 Hz sine wave)
        t = self.time_counter + np.arange(num_samples) / sample_rate
        powerline_noise = self.powerline_noise_amplitude * np.sin(2 * np.pi * 50.0 * t)
        self.time_counter += num_samples / sample_rate

        for ch in self.target_channels:
            if ch in eeg_channels:
                # Update impedance in digital twin to spike value
                twin.update_impedance(ch, self.spike_value)

                # Zero out clean signal and inject powerline noise + high random noise
                high_noise = (rng if rng is not None else np.random).normal(0, 30.0, size=num_samples)
                mutated_data[ch, :] = powerline_noise + high_noise

        return mutated_data

    def revert(self, twin: DigitalTwin) -> None:
        """Revert impedance to nominal 5.0 kOhm."""
        for ch in self.target_channels:
            twin.update_impedance(ch, 5.0)


class SignalSuppressionAttack(ISignalModifier):
    def __init__(self, target_channels: List[int], attenuation_factor: float = 0.05):
        self.target_channels = target_channels
        self.attenuation_factor = attenuation_factor

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        mutated_data = data.copy()
        for ch in self.target_channels:
            if ch in eeg_channels:
                # Attenuate the signal
                mutated_data[ch, :] *= self.attenuation_factor
        return mutated_data


