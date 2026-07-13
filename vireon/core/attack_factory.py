import numpy as np
from typing import List, Type
from vireon.core.attack import ISignalModifier
from vireon.core.twin import DigitalTwin
from vireon.plugins.clinical.qif_registry import QIFRegistry, QIFThreatTechnique

class DynamicQIFAttack(ISignalModifier):
    """
    Base class for dynamically generated QIF attacks.
    """
    def __init__(self, target_channels: List[int], technique: QIFThreatTechnique):
        self.target_channels = target_channels
        self.technique = technique

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
        return data

class AttackFactory:
    """
    Procedurally generates executable attack classes based on QIF tactics/categories.
    """

    @staticmethod
    def _create_apply_method(category: str):
        # We use closure to generate dynamic apply methods
        def apply_signal_injection(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
            mutated = data.copy()
            for ch in self.target_channels:
                if ch in eeg_channels:
                    # Inject 50uV Gaussian noise for SI
                    noise = np.random.normal(0, 50.0, size=data.shape[1])
                    mutated[ch, :] += noise
            twin.set_clinical_alert(True, f"IDS Alert: {self.technique.id} ({self.technique.name}) Active")
            return mutated

        def apply_denial_of_service(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
            mutated = data.copy()
            for ch in self.target_channels:
                if ch in eeg_channels:
                    # Ground the signal
                    mutated[ch, :] = 0.0
            twin.set_clinical_alert(True, f"IDS Alert: {self.technique.id} ({self.technique.name}) Active")
            return mutated

        def apply_data_manipulation(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
            mutated = data.copy()
            dt = data.shape[1] / sample_rate
            drift_rate = 20.0
            for ch in self.target_channels:
                if ch in eeg_channels:
                    # Induce linear drift
                    drift_vector = np.linspace(0, drift_rate * dt, data.shape[1])
                    mutated[ch, :] += drift_vector
            twin.set_clinical_alert(True, f"IDS Alert: {self.technique.id} ({self.technique.name}) Active")
            return mutated

        def apply_eavesdropping(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
            # SE doesn't change the signal, but leaves a footprint (e.g. quantum disturbance)
            twin.set_clinical_alert(True, f"Heisenberg Footprint Detected: {self.technique.name}")
            return data

        if category == "SI":
            return apply_signal_injection
        elif category in ["DS", "PE"]:
            return apply_denial_of_service
        elif category in ["DM", "CI", "EX"]:
            return apply_data_manipulation
        elif category in ["SE", "PS"]:
            return apply_eavesdropping
        else:
            # Fallback to noise injection
            return apply_signal_injection

    @classmethod
    def create_from_qif(cls, technique_id: str, target_channels: List[int]) -> ISignalModifier:
        technique = QIFRegistry.get_technique(technique_id)
        if not technique:
            raise ValueError(f"QIF Technique {technique_id} not found in the offline registry.")

        # Procedurally generate a new class named after the ID
        class_name = f"QIFAttack_{technique.id.replace('-', '_')}"
        
        # Determine the apply method based on category/tactic
        apply_method = cls._create_apply_method(technique.category)

        # Create the class dynamically
        DynamicClass = type(
            class_name,
            (DynamicQIFAttack,),
            {
                "apply": apply_method
            }
        )

        return DynamicClass(target_channels=target_channels, technique=technique)
