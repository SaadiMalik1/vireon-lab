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
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from vireon.sdk.utils import calculate_rms
from vireon.sdk.interfaces import IProvider, OrchestratorContext
from vireon.sdk.manifest import CapabilityManifest
from vireon.runtime.twin import DigitalTwin

class IClinicalEvaluator(ABC):
    @abstractmethod
    def process_signal(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int):
        """
        Monitors incoming signals and twin parameters to calculate
        decoder confidence and safety limits.
        """
        pass

    @abstractmethod
    def get_clinical_summary(self) -> Dict[str, Any]:
        """Returns a snapshot of the clinical status (Nominal, Interrupted, etc.)."""
        pass

class UncontrolledStimulationAttack:
    """
    Firmware Command Injection Attack.
    Overrides closed-loop control algorithms to force a dangerous continuous
    10.0 mA stimulation amplitude, bypassing software thresholds.
    """
    def __init__(self, twin: DigitalTwin):
        self.twin = twin

    def apply(self):
        # Force stimulator active and override safety thresholds
        self.twin.update_therapy(True)
        self.twin.update_stimulation_params(10.0, 130.0) # 10 mA (Dangerous current limit)
        self.twin.set_clinical_alert(True, "Uncontrolled Stimulation")


class ClosedLoopSimulator(IProvider, IClinicalEvaluator):
    def __init__(self, twin: DigitalTwin = None):
        self.twin = twin
        self.history_confidences: List[float] = []
        self.hazard_state = "NOMINAL"
        self.iso_severity = "NEGLIGIBLE"
        self.tissue_damage_risk = "NONE"
        self.clinical_action = "MONITOR"
        
    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            name="closed_loop_simulator",
            version="1.0.0",
            category="clinical",
            reads_state=["*"],
            mutates_state=["*"],
            publishes_events=["clinical.alert", "device.stimulate"]
        )
        
    def initialize(self, context: OrchestratorContext) -> None:
        self.context = context
        # Retrieve legacy twin if not provided in constructor
        if not self.twin:
            self.twin = context.state_store.get("legacy_twin")

    def on_tick(self, sim_clock: float, dt: float) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def process_signal(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int):
        # 1. Fetch current digital twin state
        twin_state = self.twin.get_state()
        
        # If the device is reported as disconnected, suspend therapy immediately
        if not twin_state["connected"]:
            self.twin.update_therapy(False)
            self.twin.update_stimulation_params(0.0, 0.0)
            self.twin.set_clinical_alert(True, "Link Outage")
            self.twin.update_decoder_confidence(0.0)
            self._update_risk_metrics("THERAPY_SUSPENDED")
            return

        # Check if the device is currently locked in Uncontrolled Stimulation (Attack)
        if twin_state["stimulation_amplitude_ma"] >= 10.0:
            self._update_risk_metrics("UNCONTROLLED_STIMULATION")
            return

        # Check if DBS Pathological Sync occurred
        if twin_state["clinical_status"] == "Pathological Sync Alert":
            self._update_risk_metrics("PATHOLOGICAL_SYNCHRONIZATION")
            return

        # 2. Check signal quality and calculate confidence
        base_confidence = 0.98
        penalties = 0.0
        
        bad_electrodes = 0
        high_noise_channels = 0
        suppressed_channels = 0
        
        # Analyze each EEG channel
        for ch in eeg_channels:
            # Check impedance from digital twin state
            impedance = twin_state["electrode_impedances"].get(ch, twin_state["electrode_impedances"].get(str(ch), 5.0))

            if impedance > 25.0:  # Threshold for bad contact
                bad_electrodes += 1
                penalties += 0.25
                
            # Compute RMS of signal
            if ch < data.shape[0]:
                ch_signal = data[ch, :]
                rms = calculate_rms(ch_signal)
                
                # Signal suppression check
                if rms < 0.5:
                    suppressed_channels += 1
                    penalties += 0.15
                # High noise/artifact check
                elif rms > 120.0:
                    high_noise_channels += 1
                    penalties += 0.20
        
        # Calculate final confidence (must be between 0.0 and 1.0)
        calculated_confidence = max(0.0, base_confidence - penalties)
        self.twin.update_decoder_confidence(calculated_confidence)
        self.history_confidences.append(calculated_confidence)
        
        # 3. Decision Logic for Closed-Loop Therapy
        severe_impedance = any(v > 50.0 for v in self.twin.electrode_impedances.values())
        
        if severe_impedance:
            self.twin.update_therapy(False)
            self.twin.update_stimulation_params(0.0, 0.0)
            self.twin.set_clinical_alert(True, "High Impedance Alert")
            self._update_risk_metrics("THERAPY_SUSPENDED")
            
        elif calculated_confidence < 0.70:
            self.twin.update_therapy(False)
            self.twin.update_stimulation_params(0.0, 0.0)
            self.twin.set_clinical_alert(True, "Low Confidence Interruption")
            self._update_risk_metrics("THERAPY_SUSPENDED")
            
        elif calculated_confidence < 0.90 or bad_electrodes > 0:
            # Low signal quality warning, but therapy continues
            self.twin.update_therapy(True)
            self.twin.update_stimulation_params(2.0, 130.0)
            self.twin.set_clinical_alert(False, "Signal Warning")
            self._update_risk_metrics("WARNING")
        else:
            # Nominal operating state
            self.twin.update_therapy(True)
            self.twin.update_stimulation_params(2.0, 130.0) # 2.0 mA @ 130 Hz
            self.twin.set_clinical_alert(False, "Nominal")
            self._update_risk_metrics("NOMINAL")

    def _update_risk_metrics(self, state: str):
        self.hazard_state = state
        if state == "NOMINAL":
            self.iso_severity = "NEGLIGIBLE"
            self.tissue_damage_risk = "NONE"
            self.clinical_action = "MONITOR"
        elif state == "WARNING":
            self.iso_severity = "MARGINAL"
            self.tissue_damage_risk = "NONE"
            self.clinical_action = "MONITOR"
        elif state == "THERAPY_SUSPENDED":
            self.iso_severity = "MARGINAL"
            self.tissue_damage_risk = "NONE"
            self.clinical_action = "SUSPEND_THERAPY"
        elif state == "PATHOLOGICAL_SYNCHRONIZATION":
            self.iso_severity = "CRITICAL"
            self.tissue_damage_risk = "MEDIUM"
            self.clinical_action = "SYNC_ALERT"
        elif state == "UNCONTROLLED_STIMULATION":
            self.iso_severity = "CATASTROPHIC"
            self.tissue_damage_risk = "HIGH"
            self.clinical_action = "SHUTDOWN_HARDWARE"
            
        self.twin.update_clinical_risk(
            self.hazard_state,
            self.iso_severity,
            self.tissue_damage_risk,
            self.clinical_action
        )

    def get_clinical_summary(self) -> Dict[str, Any]:
        state = self.twin.get_state()
        avg_conf = np.mean(self.history_confidences) if self.history_confidences else 1.0
        return {
            "device_id": state["device_id"],
            "current_status": state["clinical_status"],
            "alert_active": state["clinical_alert_active"],
            "therapy_enabled": state["stimulation_enabled"],
            "average_confidence": round(float(avg_conf), 3),
            "min_confidence": round(float(np.min(self.history_confidences)), 3) if self.history_confidences else 1.0,
            "stimulation_amplitude_ma": state["stimulation_amplitude_ma"],
            "stimulation_frequency_hz": state["stimulation_frequency_hz"],
            "hazard_state": self.hazard_state,
            "iso_severity": self.iso_severity,
            "tissue_damage_risk": self.tissue_damage_risk,
            "clinical_action": self.clinical_action
        }
