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
from typing import List, Dict, Any
from vireon.sdk.state import IStateStore as StateStore
from vireon.sdk.utils import calculate_bandpower


class LFPGenerator:
    """
    Generates synthetic Subthalamic Nucleus (STN) Local Field Potentials (LFPs).
    Simulates pathological Parkinsonian beta bursts (13-30 Hz) modulated
    by slowly oscillating envelopes and suppressed/amplified by stimulation.
    """
    def __init__(self, sample_rate: int = 250, num_channels: int = 8):
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        self.tick = 0
        
        # State variables representing the pathological biomarker state
        self.base_beta_amplitude = 45.0  # Nominal amplitude in microvolts

    def read_chunk(self, num_samples: int, stimulation_state: str) -> np.ndarray:
        """
        stimulation_state can be:
        - "none": no stimulation (beta bursts are nominal)
        - "suppress": therapeutic out-of-phase stimulation (beta amplitude decreases)
        - "sync": pathological in-phase stimulation (beta amplitude increases)
        """
        # Dynamically adjust the underlying pathological beta amplitude based on stimulation
        if stimulation_state == "suppress":
            # Slowly suppress the tremor beta rhythm
            self.base_beta_amplitude = max(10.0, self.base_beta_amplitude - 0.5 * (num_samples / self.sample_rate))
        elif stimulation_state == "sync":
            # Pathological synchronization amplifies the tremor rhythm
            self.base_beta_amplitude = min(120.0, self.base_beta_amplitude + 1.5 * (num_samples / self.sample_rate))
        else:
            # Return slowly to nominal pathological base state (tremor recurrence)
            if self.base_beta_amplitude < 45.0:
                self.base_beta_amplitude += 0.2 * (num_samples / self.sample_rate)
            elif self.base_beta_amplitude > 45.0:
                self.base_beta_amplitude -= 0.5 * (num_samples / self.sample_rate)

        t = (self.tick + np.arange(num_samples)) / self.sample_rate
        self.tick += num_samples

        data = np.zeros((self.num_channels, num_samples))
        
        # Helper for 1/f^alpha (pink) noise
        def generate_pink_noise(n_samples, alpha=1.5):
            white = np.random.normal(0, 1, n_samples)
            X_white = np.fft.rfft(white)
            # Power law 1/f^(alpha/2) for amplitude spectrum
            f = np.fft.rfftfreq(n_samples)
            f[0] = 1e-10 # Avoid division by zero
            S = X_white / (f ** (alpha / 2.0))
            # Normalize to preserve variance roughly
            S = S / np.sqrt(np.mean(np.abs(S)**2))
            return np.fft.irfft(S, n=n_samples)
            
        # Generate pink noise background
        pink_noise = generate_pink_noise(num_samples, alpha=1.5) * 5.0
        
        # Channel 0 represents the STN LFP signal
        # Pathological Beta rhythm (20 Hz) + frequency variation
        beta_freqs = 20.0 + 1.5 * np.sin(2 * np.pi * 0.1 * t) # Drift
        beta_signal = np.sin(2 * np.pi * beta_freqs * t)
        
        # Bursty modulator envelope
        # Instead of continuous sine, use thresholded noise for burstiness
        burst_noise = generate_pink_noise(num_samples, alpha=2.0) # Brownian-like
        envelope = np.clip(burst_noise + 0.5, 0, None) # Positive bursts
        envelope = envelope / (np.max(envelope) + 1e-5) # Normalize 0-1
        
        # Compute final signal for LFP channel
        data[0, :] = self.base_beta_amplitude * envelope * beta_signal + pink_noise
        
        # Make other channels contain standard pink noise activity
        for ch in range(1, self.num_channels):
            data[ch, :] = generate_pink_noise(num_samples, alpha=1.0) * 3.0
            
        return data

class ClosedLoopDBSController:
    """
    Closed-loop Deep Brain Stimulation (DBS) Controller.
    Computes beta band power and phase-locked triggers.
    Supports phase-shifting attacks that lead to pathological synchronization.
    """
    def __init__(self, twin: DigitalTwin):
        self.twin = twin
        self.lfp_generator = LFPGenerator(twin.sample_rate, twin.num_channels)
        self.feedback_buffer = np.zeros(0)
        self.stimulation_mode = "none" # "none", "suppress", "sync"
        self.history_beta_power: list[float] = []
        self.attack_duration_ticks = 0

    def process_lfp(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, attack_active: bool):
        # STN LFP is on channel 0
        lfp = data[0, :]
        
        # Accumulate feedback buffer (keep last 250 samples for FFT calculations)
        self.feedback_buffer = np.concatenate((self.feedback_buffer, lfp)) # type: ignore
        if len(self.feedback_buffer) > 250:
            self.feedback_buffer = self.feedback_buffer[-250:] # type: ignore

        # 1. Apply phase-shifting attack if active on feedback path
        # A 180-degree phase shift at 20 Hz (period = 12.5 samples at 250Hz) is equal to 6 samples delay
        analysis_buffer = self.feedback_buffer
        if attack_active:
            self.attack_duration_ticks += len(lfp)
        else:
            self.attack_duration_ticks = 0

        if attack_active and len(analysis_buffer) >= 6:
            # Shift buffer by 6 samples to emulate 180 degrees delay
            analysis_buffer = np.roll(analysis_buffer, 6) # type: ignore

        # 2. Compute beta power and phase
        n = len(analysis_buffer)
        if n < 50:
            return
            
        # Get current beta-band power (13-30 Hz)
        beta_power = calculate_bandpower(analysis_buffer, sample_rate, (13.0, 30.0))
        self.history_beta_power.append(beta_power)
        # Cap history size
        if len(self.history_beta_power) > 1000:
            self.history_beta_power.pop(0)
        
        # Estimate phase using rfft
        fft_vals = np.fft.rfft(analysis_buffer)
        fft_freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
        
        # Peak frequency in beta band
        beta_idx = np.where((fft_freqs >= 13.0) & (fft_freqs <= 30.0))[0]
        if len(beta_idx) > 0:
            _peak_idx = beta_idx[np.argmax(np.abs(fft_vals[beta_idx]))]
            # Phase angle in radians (-pi to pi)
            pass
        else:
            pass

        # 3. Decision loop
        # If the security layer has shut off therapy due to detected sync, do not re-enable
        state_curr = self.twin.get_state()
        if state_curr["clinical_status"] == "IDS Suspend: Sync Detected":
            self.stimulation_mode = "none"
            self.twin.update_therapy(False)
            self.twin.update_stimulation_params(0.0, 0.0)
            return

        # Trigger closed-loop DBS stimulation when beta power exceeds biomarker threshold
        # Nominal threshold is 25.0 uV^2
        threshold = 25.0
        
        if beta_power > threshold:
            # If the feedback phase is delayed/shifted, the stimulator fires in-phase with the true rhythm
            if attack_active:
                # In-phase synchronization exacerbates symptoms
                self.stimulation_mode = "sync"
                self.twin.update_therapy(True)
                self.twin.update_stimulation_params(amplitude=3.0, frequency=130.0)
                self.twin.set_clinical_alert(True, "Pathological Sync Alert")
                # Drop confidence to 0.0 indicating symptoms out of control
                self.twin.update_decoder_confidence(0.0)
                
                # Standards mapping evaluation for Phase-Shift Attack
                self.twin.update_clinical_risk(
                    "PATHOLOGICAL_SYNCHRONIZATION", 
                    "CATASTROPHIC", 
                    "MEDIUM", 
                    "SYNC_ALERT",
                    dsm5_diagnosis="F32_MAJOR_DEPRESSION",
                    diagnostic_cluster="MOOD",
                    niss_score=10.0
                )
            else:
                # Out-of-phase stimulation suppresses pathological oscillations
                self.stimulation_mode = "suppress"
                self.twin.update_therapy(True)
                self.twin.update_stimulation_params(amplitude=2.5, frequency=130.0)
                self.twin.set_clinical_alert(False, "Nominal Stimulation")
                # Confidence remains high (rhythm under control)
                self.twin.update_decoder_confidence(0.95)
                self.twin.update_clinical_risk("NOMINAL", "NEGLIGIBLE", "NONE", "MONITOR")
        else:
            # Beta power is below threshold, turn off stimulator to conserve battery (closed-loop)
            self.stimulation_mode = "none"
            self.twin.update_therapy(False)
            self.twin.update_stimulation_params(0.0, 0.0)
            if attack_active:
                self.twin.set_clinical_alert(True, "Pathological Sync Alert")
                self.twin.update_decoder_confidence(0.0)
                self.twin.update_clinical_risk(
                    "PATHOLOGICAL_SYNCHRONIZATION", 
                    "CATASTROPHIC", 
                    "MEDIUM", 
                    "SYNC_ALERT",
                    dsm5_diagnosis="F32_MAJOR_DEPRESSION",
                    diagnostic_cluster="MOOD",
                    niss_score=10.0
                )
            else:
                self.twin.set_clinical_alert(False, "Nominal Suppression")
                self.twin.update_decoder_confidence(0.95)
                self.twin.update_clinical_risk("NOMINAL", "NEGLIGIBLE", "NONE", "MONITOR")

    def get_clinical_summary(self) -> Dict[str, Any]:
        state = self.twin.get_state()
        avg_power = np.mean(self.history_beta_power) if self.history_beta_power else 0.0
        return {
            "device_id": state["device_id"],
            "current_status": state["clinical_status"],
            "alert_active": state["clinical_alert_active"],
            "therapy_enabled": state["stimulation_enabled"],
            "average_beta_power": round(float(avg_power), 2),
            "stimulation_amplitude_ma": state["stimulation_amplitude_ma"],
            "stimulation_frequency_hz": state["stimulation_frequency_hz"],
            "decoder_confidence": state["decoder_confidence"],
            "average_confidence": state["decoder_confidence"],
            "min_confidence": state["decoder_confidence"],
            "hazard_state": state["hazard_state"],
            "iso_severity": state["iso_severity"],
            "tissue_damage_risk": state["tissue_damage_risk"],
            "clinical_action": state["clinical_action"]
        }
