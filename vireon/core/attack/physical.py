import numpy as np
from typing import List, Optional
from vireon.core.twin import DigitalTwin

from .base import ISignalModifier

class ElectrodeSaturationAttack(ISignalModifier):
    def __init__(self, target_channels: List[int]):
        self.target_channels = target_channels
    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        mutated = data.copy()
        for ch in self.target_channels:
            if ch in eeg_channels: 
                mutated[ch, :] = 1e6 # Max ADC value representation
        return mutated


class PacketLossAttack(ISignalModifier):
    def __init__(self, target_channels: List[int], drop_prob: float = 0.1):
        self.target_channels = target_channels
        self.drop_prob = drop_prob
    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        mutated = data.copy()
        mask = (rng if rng is not None else np.random).random(data.shape[1]) < self.drop_prob
        for ch in self.target_channels:
            if ch in eeg_channels: 
                mutated[ch, mask] = 0.0
        return mutated


class TimingJitterAttack(ISignalModifier):
    def __init__(self, target_channels: List[int], jitter_ms: float = 2.0):
        self.target_channels = target_channels
        self.jitter_ms = jitter_ms
    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        mutated = data.copy()
        for ch in self.target_channels:
            if ch in eeg_channels:
                shift = int((self.jitter_ms / 1000.0) * sample_rate)
                if shift > 0: 
                    mutated[ch, :] = np.roll(mutated[ch, :], shift)
        return mutated


class DropoutAttack(ISignalModifier):
    def __init__(self, target_channels: List[int], dropout_length_sec: float = 0.5):
        self.target_channels = target_channels
        self.dropout_length_sec = dropout_length_sec
    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        mutated = data.copy()
        drop_samples = int(self.dropout_length_sec * sample_rate)
        if drop_samples > 0 and drop_samples < data.shape[1]:
            start_idx = (rng if rng is not None else np.random).integers(0, data.shape[1] - drop_samples)
            for ch in self.target_channels:
                if ch in eeg_channels: 
                    mutated[ch, start_idx:start_idx+drop_samples] = 0.0
        return mutated


class ClippingAttack(ISignalModifier):
    def __init__(self, target_channels: List[int], clip_value: float = 100.0):
        self.target_channels = target_channels
        self.clip_value = clip_value
    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        mutated = data.copy()
        for ch in self.target_channels:
            if ch in eeg_channels: 
                mutated[ch, :] = np.clip(mutated[ch, :], -self.clip_value, self.clip_value)
        return mutated


class AmplifierSaturationAttack(ISignalModifier):
    def __init__(self, target_channels: List[int]):
        self.target_channels = target_channels
    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        mutated = data.copy()
        for ch in self.target_channels:
            if ch in eeg_channels: 
                mutated[ch, :] = np.where(mutated[ch, :] > 0, 500.0, -500.0)
        return mutated


class EMIAttack(ISignalModifier):
    def __init__(self, target_channels: List[int]):
        self.target_channels = target_channels
        self.time_counter = 0.0
    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        mutated = data.copy()
        t = self.time_counter + np.arange(data.shape[1]) / sample_rate
        self.time_counter += data.shape[1] / sample_rate
        emi = 200.0 * np.sin(2 * np.pi * 50.0 * t) + 100.0 * np.sin(2 * np.pi * 60.0 * t)
        for ch in self.target_channels:
            if ch in eeg_channels: 
                mutated[ch, :] += emi
        return mutated


class MotionArtifactAttack(ISignalModifier):
    def __init__(self, target_channels: List[int]):
        self.target_channels = target_channels
    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        mutated = data.copy()
        for ch in self.target_channels:
            if ch in eeg_channels:
                artifact = (rng if rng is not None else np.random).normal(0, 150.0, size=(data.shape[1],))
                # low-pass filter the artifact to simulate motion
                artifact_filtered = np.convolve(artifact, np.ones(10)/10, mode='same')
                mutated[ch, :] += artifact_filtered
        return mutated


class CrossTalkAttack(ISignalModifier):
    def __init__(self, target_channels: List[int], source_channel: int = 0, crosstalk_factor: float = 0.3):
        self.target_channels = target_channels
        self.source_channel = source_channel
        self.crosstalk_factor = crosstalk_factor
    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        mutated = data.copy()
        if self.source_channel in eeg_channels:
            source_data = data[self.source_channel, :]
            for ch in self.target_channels:
                if ch in eeg_channels and ch != self.source_channel:
                    mutated[ch, :] += source_data * self.crosstalk_factor
        return mutated


class ClockSkewAttack(ISignalModifier):
    def __init__(self, target_channels: List[int], skew_rate: float = 0.01):
        self.target_channels = target_channels
        self.skew_rate = skew_rate
    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        # Simplistic representation of clock skew as a slight drift in data interpolation
        mutated = data.copy()
        num_samples = data.shape[1]
        indices = np.arange(num_samples)
        skewed_indices = np.clip(indices * (1.0 + self.skew_rate), 0, num_samples - 1).astype(int)
        for ch in self.target_channels:
            if ch in eeg_channels:
                mutated[ch, :] = mutated[ch, skewed_indices]
        return mutated


