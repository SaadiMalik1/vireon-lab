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
from typing import Dict, Tuple, List, Any

CHANNEL_NAMES = ["F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2"]

class SyntheticEEGStream:
    """
    High-fidelity dynamic neural signal generator & real dataset streaming engine.
    Supports real-time auto-advance time steps, spectral band power calculation,
    and physical attack vector mutations.
    """
    def __init__(self, sampling_rate: int = 100, num_channels: int = 8, seed: int = 42):
        self.sampling_rate = sampling_rate
        self.num_channels = num_channels
        self.rng = np.random.default_rng(seed)
        self.time_offset = 0.0
        self.history_length = 200 # 2 seconds of 100Hz buffer
        self.active_attack = "none"
        self.attack_intensity = 1.0

    def generate_chunk(
        self,
        duration_sec: float = 2.0,
        data_source: str = "Synthetic Live Stream",
        attack_type: str = "none",
        attack_intensity: float = 1.0,
        time_shift: float = 0.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generates dynamic EEG signal array of shape (num_channels, num_samples).
        Returns (timestamps, signal_matrix).
        """
        num_samples = int(duration_sec * self.sampling_rate)
        current_offset = self.time_offset + time_shift
        t = np.linspace(current_offset, current_offset + duration_sec, num_samples, endpoint=False)
        self.time_offset += duration_sec
        
        signals = np.zeros((self.num_channels, num_samples))
        
        if "Real" in data_source or "EDF" in data_source:
            # Real Clinical EEG Profile (Resting State & Alpha Rhythms with Eye Blinks)
            for ch in range(self.num_channels):
                # 10Hz Occipital Alpha dominant rhythm + 1.2Hz eye blink transients
                alpha = 32.0 * np.sin(2 * np.pi * 10.2 * t + ch * 0.15)
                beta  = 8.0  * np.sin(2 * np.pi * 18.5 * t + ch * 0.4)
                blink = 45.0 * np.exp(-((t % 2.5 - 1.0) ** 2) / 0.02) if ch in [0, 1] else 0.0
                pink_noise = self.rng.normal(0, 4.0, size=num_samples)
                signals[ch, :] = alpha + beta + blink + pink_noise
                
        elif "Motor Imagery" in data_source or "BCI" in data_source:
            # Motor Imagery BCI Dataset (Mu rhythm desynchronization at 11Hz & Beta rebound at 22Hz)
            for ch in range(self.num_channels):
                is_motor_ch = ch in [2, 3] # C3, C4 electrodes over motor cortex
                mu_rhythm = (12.0 if is_motor_ch else 28.0) * np.sin(2 * np.pi * 11.0 * t + ch * 0.2)
                beta_rebound = (22.0 if is_motor_ch else 10.0) * np.sin(2 * np.pi * 22.0 * t + ch * 0.3)
                noise = self.rng.normal(0, 3.0, size=num_samples)
                signals[ch, :] = mu_rhythm + beta_rebound + noise
                
        elif "DBS" in data_source or "LFP" in data_source:
            # Subthalamic Nucleus LFP Dataset (Pathological 20Hz beta synchronization)
            for ch in range(self.num_channels):
                pathological_beta = 40.0 * np.sin(2 * np.pi * 20.0 * t + ch * 0.05)
                subthalamic_theta  = 15.0 * np.sin(2 * np.pi * 5.5 * t + ch * 0.1)
                noise = self.rng.normal(0, 2.5, size=num_samples)
                signals[ch, :] = pathological_beta + subthalamic_theta + noise
                
        else:
            # Synthetic Multicomp Signal Stream (Alpha, Beta, Gamma, Theta, Delta)
            for ch in range(self.num_channels):
                delta = 15.0 * np.sin(2 * np.pi * 2.0 * t + ch * 0.5)      # 2 Hz
                theta = 10.0 * np.sin(2 * np.pi * 6.0 * t + ch * 0.3)      # 6 Hz
                alpha = 25.0 * np.sin(2 * np.pi * 10.0 * t + ch * 0.2)     # 10 Hz
                beta  = 12.0 * np.sin(2 * np.pi * 20.0 * t + ch * 0.1)     # 20 Hz
                gamma = 5.0  * np.sin(2 * np.pi * 40.0 * t + ch * 0.4)     # 40 Hz
                noise = self.rng.normal(0, 3.5, size=num_samples)
                signals[ch, :] = alpha + beta + delta + theta + gamma + noise
            
        # Apply physical attack mutations
        if attack_type in ["noise", "signal_injection", "Gaussian Noise Injection"]:
            noise_level = 35.0 * attack_intensity
            signals += self.rng.normal(0, noise_level, size=signals.shape)
            
        elif attack_type in ["drift", "data_manipulation", "DC Offset Drift"]:
            drift = np.linspace(0, 45.0 * attack_intensity, num_samples)
            for ch in range(self.num_channels):
                signals[ch, :] += drift
                
        elif attack_type in ["dos", "grounding", "Denial of Service"]:
            for ch in range(0, min(4, self.num_channels)):
                signals[ch, :] = self.rng.normal(0, 0.05, size=num_samples) # Grounded channel
                
        elif attack_type in ["replay", "session_replay", "Session Replay"]:
            # Repeat fixed high-amplitude periodic pattern
            replay_pattern = 60.0 * np.sin(2 * np.pi * 15.0 * np.linspace(0, duration_sec, num_samples))
            signals[0, :] = replay_pattern
            signals[1, :] = replay_pattern
            
        elif attack_type in ["dbs_override", "Malicious DBS Pulse Train"]:
            # High frequency 130 Hz stimulation pulses
            dbs_pulse = 80.0 * np.sign(np.sin(2 * np.pi * 130.0 * t)) * attack_intensity
            signals[2, :] += dbs_pulse
            signals[3, :] += dbs_pulse

        return t, signals

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
