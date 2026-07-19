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

"""
Adversarial Machine Learning Attacks for BCI Decoders.

This module provides signal modifiers that simulate adversarial attacks
against the downstream ML decoder (e.g. MLTremorDecoder).
It includes approximations of FGSM, PGD, and C&W attacks tailored for
time-series signal classification, as well as a Backdoor Trigger Injector
for training-time poisoning simulations.

References:
  - Adversarial Attacks on EEG-based Brain-Computer Interfaces (2024-2025)
"""

import numpy as np
from typing import List

from vireon.runtime.attack import ISignalModifier
from vireon.runtime.twin import DigitalTwin

try:
    import importlib.util
    TORCH_AVAILABLE = importlib.util.find_spec('torch') is not None
except ImportError:
    TORCH_AVAILABLE = False


class FGSMAttack(ISignalModifier):
    """
    Fast Gradient Sign Method (FGSM) approximation for BCI signals.
    
    Since the true model gradient may not be available online, this
    simulates an FGSM attack by adding scaled adversarial noise that
    maximizes variance/power, specifically targeting simple RMS decoders.
    """
    def __init__(self, target_channels: List[int], epsilon: float = 10.0):
        self.target_channels = target_channels
        self.epsilon = epsilon

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: np.random.Generator | None = None) -> np.ndarray:
        mutated_data = data.copy()
        
        # Approximate gradient sign by taking the sign of the signal itself
        # (amplifies the peaks, increasing RMS power maximally)
        gradient_sign = np.sign(data)
        
        for ch in self.target_channels:
            if ch in eeg_channels:
                mutated_data[ch, :] += self.epsilon * gradient_sign[ch, :]
                
        return mutated_data


class PGDAttack(ISignalModifier):
    """
    Projected Gradient Descent (PGD) approximation for BCI signals.
    
    Simulates a stronger, iterative adversarial attack. For the MLTremorDecoder,
    this attempts to craft a perturbation that perfectly offsets the signal
    power or artificially inflates it, clamped to L-infinity norm `epsilon`.
    """
    def __init__(self, target_channels: List[int], epsilon: float = 15.0, alpha: float = 2.0, steps: int = 5):
        self.target_channels = target_channels
        self.epsilon = epsilon
        self.alpha = alpha
        self.steps = steps

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: np.random.Generator | None = None) -> np.ndarray:
        mutated_data = data.copy()
        
        for ch in self.target_channels:
            if ch in eeg_channels:
                original = data[ch, :]
                adv_signal = original.copy()
                
                # PGD iteration loop
                for _ in range(self.steps):
                    # Direction to maximize power
                    grad_sign = np.sign(adv_signal)
                    adv_signal = adv_signal + self.alpha * grad_sign
                    
                    # Project back to L-infinity epsilon ball around original
                    eta = np.clip(adv_signal - original, -self.epsilon, self.epsilon)
                    adv_signal = original + eta
                    
                mutated_data[ch, :] = adv_signal
                
        return mutated_data


class CWAttack(ISignalModifier):
    """
    Carlini & Wagner (C&W) approximation.
    
    This simulates an optimized, low-distortion adversarial attack. It injects
    a highly targeted frequency component (e.g. tremor frequency) at the minimal
    amplitude required to cross the decoder's decision boundary.
    """
    def __init__(self, target_channels: List[int], target_frequency_hz: float = 5.0, target_amplitude_uv: float = 6.0):
        self.target_channels = target_channels
        self.target_frequency = target_frequency_hz
        self.target_amplitude = target_amplitude_uv
        self.phase = 0.0

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: np.random.Generator | None = None) -> np.ndarray:
        mutated_data = data.copy()
        num_samples = data.shape[1]
        t = np.arange(num_samples) / sample_rate
        
        # Continuous phase across chunks
        phase_arr = 2 * np.pi * self.target_frequency * t + self.phase
        self.phase = (phase_arr[-1] + (2 * np.pi * self.target_frequency * (1/sample_rate))) % (2 * np.pi)
        
        cw_perturbation = self.target_amplitude * np.sin(phase_arr)
        
        for ch in self.target_channels:
            if ch in eeg_channels:
                mutated_data[ch, :] += cw_perturbation
                
        return mutated_data


class BackdoorTriggerInjector(ISignalModifier):
    """
    Data poisoning attack simulation.
    
    Injects a specific, hidden trigger waveform (e.g., 20Hz at 30uV). If this
    is applied during training/calibration, the autoencoder learns to ignore it.
    If applied at inference, it triggers the backdoor.
    """
    def __init__(self, target_channels: List[int], trigger_frequency_hz: float = 20.0, trigger_amplitude_uv: float = 30.0):
        self.target_channels = target_channels
        self.trigger_frequency = trigger_frequency_hz
        self.trigger_amplitude = trigger_amplitude_uv
        self.phase = 0.0

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: np.random.Generator | None = None) -> np.ndarray:
        mutated_data = data.copy()
        num_samples = data.shape[1]
        t = np.arange(num_samples) / sample_rate
        
        phase_arr = 2 * np.pi * self.trigger_frequency * t + self.phase
        self.phase = (phase_arr[-1] + (2 * np.pi * self.trigger_frequency * (1/sample_rate))) % (2 * np.pi)
        
        trigger_wave = self.trigger_amplitude * np.sin(phase_arr)
        
        for ch in self.target_channels:
            if ch in eeg_channels:
                mutated_data[ch, :] += trigger_wave
                
        return mutated_data
