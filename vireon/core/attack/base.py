from abc import ABC, abstractmethod
import numpy as np
from typing import List, Optional
from vireon.core.twin import DigitalTwin


class ISignalModifier(ABC):
    @abstractmethod
    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        """
        Mutates the incoming signal window and registers impacts
        on the DigitalTwin state (e.g. impedance changes, disconnection).
        """
        pass

    def revert(self, twin: DigitalTwin) -> None:
        """
        Reverts any persistent state changes made to the DigitalTwin when 
        the modifier is removed. Base implementation does nothing.
        """
        pass

