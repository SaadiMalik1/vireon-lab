from abc import ABC, abstractmethod
from typing import List

class IDeviceWrapper(ABC):
    @abstractmethod
    def get_board(self):
        """Returns the underlying configured BrainFlow BoardShim instance."""
        pass

    @abstractmethod
    def get_eeg_channels(self) -> List[int]:
        """Returns the list of indices mapping to EEG data channels."""
        pass
