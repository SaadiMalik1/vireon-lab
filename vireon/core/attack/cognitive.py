import numpy as np
from typing import List, Optional
from vireon.core.twin import DigitalTwin

from .base import ISignalModifier

class NeuroPhishingAttack(ISignalModifier):
    """
    Simulates Cognitive Warfare / Neuro-Phishing.
    Adversarial injection of specific neural patterns (e.g. SSVEP or P300-like triggers)
    to manipulate the user's emotional state or BCI cursor control.
    """
    def __init__(self, target_channels: List[int], manipulation_type: str = "emotional"):
        self.target_channels = target_channels
        self.manipulation_type = manipulation_type
        self.time_counter = 0.0

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        mutated_data = data.copy()
        num_samples = data.shape[1]
        
        # Inject an Alpha-band (10 Hz) driving frequency for emotional manipulation
        # or a 15 Hz SSVEP pattern for BCI control hijacking.
        freq = 10.0 if self.manipulation_type == "emotional" else 15.0
        
        t = self.time_counter + np.arange(num_samples) / sample_rate
        trigger_wave = 25.0 * np.sin(2 * np.pi * freq * t)
        self.time_counter += num_samples / sample_rate
        
        for ch in self.target_channels:
            if ch in eeg_channels:
                mutated_data[ch, :] += trigger_wave
                
        # Register the cognitive manipulation in the Digital Twin
        twin.set_clinical_alert(True, f"Neuro-Phishing: {self.manipulation_type.upper()} manipulation detected")
        if self.manipulation_type == "emotional":
            twin.dsm5_diagnosis = "INDUCED_MANIA"
            twin.diagnostic_cluster = "COGNITIVE_WARFARE"
            
        return mutated_data


class FirmwareRollbackAttack(ISignalModifier):
    """
    Simulates an Over-The-Air (OTA) Downgrade / Rollback Attack.
    Attempts to push a malicious firmware payload containing an older
    Security Version Number (SVN) to bypass anti-rollback protections.
    This attack doesn't mutate the signal window, but triggers the
    OTA process on the target twin/firmware.
    """
    def __init__(self, target_channels: List[int], payload_version: int = 0):
        self.target_channels = target_channels
        self.payload_version = payload_version
        self.has_fired = False

    @property
    def full_payload(self) -> bytes:
        import struct
        malicious_binary = b'A' * 600000
        header = struct.pack('<I', self.payload_version)
        dummy_signature = b'\x00' * 64
        return header + dummy_signature + malicious_binary

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        if not self.has_fired:
            # Construct a malicious payload: [Version header (4 bytes)] + [Overflow Payload]
            # Version is lower than the expected minimum (e.g., SVN 0)
            
            # Record the attempt on the Digital Twin's event log or directly via the firmware
            twin.set_clinical_alert(True, f"Malicious OTA Downgrade Attempted (SVN {self.payload_version})")
            
            # The actual OTA simulation happens in the Coordinator by invoking the firmware stub.
            # Here we just mark that the attack window triggered.
            self.has_fired = True
            
        return data

    def revert(self, twin: DigitalTwin) -> None:
        """Clear the clinical alert if it was triggered."""
        if self.has_fired:
            twin.set_clinical_alert(False, "Nominal")


class InsiderThreatAttack(ISignalModifier):
    """
    Simulates an insider threat where a compromised clinician sets dangerous
    stimulation parameters directly, bypassing normal safeguards.
    """
    def __init__(self, target_channels: List[int]):
        self.target_channels = target_channels
        self.has_fired = False

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        if not self.has_fired:
            print("[InsiderThreatAttack] Injecting malicious clinical configuration...")
            # Force a dangerous parameter directly on the twin
            if hasattr(twin, "_lock"):
                with twin._lock:
                    twin.stimulation_amplitude_ma = 15.0
                    twin.set_clinical_alert(True, "Insider Threat: Dangerous parameters injected")
            else:
                twin.stimulation_amplitude_ma = 15.0
                twin.set_clinical_alert(True, "Insider Threat: Dangerous parameters injected")
            self.has_fired = True
        return data

    def revert(self, twin: DigitalTwin) -> None:
        if self.has_fired:
            if hasattr(twin, "_lock"):
                with twin._lock:
                    twin.stimulation_amplitude_ma = 5.0
                    twin.set_clinical_alert(False, "Nominal")
            else:
                twin.stimulation_amplitude_ma = 5.0
                twin.set_clinical_alert(False, "Nominal")


