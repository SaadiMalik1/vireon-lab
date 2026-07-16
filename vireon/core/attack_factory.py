import numpy as np
from typing import List
from vireon.core.attack import ISignalModifier
from vireon.core.twin import DigitalTwin
from vireon.core.threat_intel import ThreatIntelligence

class DynamicStandardsAttack(ISignalModifier):
    """
    Base class for dynamically generated attacks based on standards mapping.
    """
    def __init__(self, target_channels: List[int], technique: dict):
        self.target_channels = target_channels
        self.technique = technique

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: np.random.Generator | None = None) -> np.ndarray:
        return data

class AttackFactory:
    """
    Procedurally generates executable attack classes based on standards tactics/categories.
    """

    @staticmethod
    def _create_apply_method(category: str):
        # We use closure to generate dynamic apply methods
        def apply_signal_injection(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: np.random.Generator | None = None) -> np.ndarray:
            mutated = data.copy()
            for ch in self.target_channels:
                if ch in eeg_channels:
                    # Inject 50uV Gaussian noise for SI
                    noise = rng.normal(0, 50.0, size=data.shape[1]) if rng is not None else np.random.normal(0, 50.0, size=data.shape[1])
                    mutated[ch, :] += noise
            twin.set_clinical_alert(True, f"IDS Alert: {self.technique.get('mitre_attack', 'Unknown')} ({self.technique.get('name', 'Unknown')}) Active")
            return mutated

        def apply_denial_of_service(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: np.random.Generator | None = None) -> np.ndarray:
            mutated = data.copy()
            for ch in self.target_channels:
                if ch in eeg_channels:
                    # Ground the signal
                    mutated[ch, :] = 0.0
            twin.set_clinical_alert(True, f"IDS Alert: {self.technique.get('mitre_attack', 'Unknown')} ({self.technique.get('name', 'Unknown')}) Active")
            return mutated

        def apply_data_manipulation(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: np.random.Generator | None = None) -> np.ndarray:
            mutated = data.copy()
            dt = data.shape[1] / sample_rate
            drift_rate = 20.0
            for ch in self.target_channels:
                if ch in eeg_channels:
                    # Induce linear drift
                    drift_vector = np.linspace(0, drift_rate * dt, data.shape[1])
                    mutated[ch, :] += drift_vector
            twin.set_clinical_alert(True, f"IDS Alert: {self.technique.get('mitre_attack', 'Unknown')} ({self.technique.get('name', 'Unknown')}) Active")
            return mutated

        def apply_eavesdropping(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: np.random.Generator | None = None) -> np.ndarray:
            twin.set_clinical_alert(True, f"Telemetry Threat Detected: {self.technique.get('name', 'Unknown')}")
            return data

        if category == "SI" or category == "Tampering":
            return apply_signal_injection
        elif category in ["DS", "PE", "Denial of Service"]:
            return apply_denial_of_service
        elif category in ["DM", "CI", "EX", "Elevation of Privilege"]:
            return apply_data_manipulation
        elif category in ["SE", "PS", "Spoofing", "Information Disclosure"]:
            return apply_eavesdropping
        else:
            # Fallback to noise injection
            return apply_signal_injection

    @classmethod
    def create_dynamic_attack(cls, technique_id: str, target_channels: List[int]) -> ISignalModifier:
        ti = ThreatIntelligence()
        technique = ti.resolve_attack(technique_id)
        if not technique:
            raise ValueError(f"Technique {technique_id} not found in the standards mapping.")

        # Procedurally generate a new class named after the ID
        class_name = f"StandardAttack_{technique_id.replace('-', '_')}"
        
        # Determine the apply method based on category/tactic
        apply_method = cls._create_apply_method(technique.get("stride", "Tampering"))

        # Create the class dynamically
        DynamicClass = type(
            class_name,
            (DynamicStandardsAttack,),
            {
                "apply": apply_method
            }
        )

        return DynamicClass(target_channels=target_channels, technique=technique)
