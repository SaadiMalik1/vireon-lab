from abc import ABC, abstractmethod
from typing import List, Any

class IDeviceWrapper(ABC):
    @abstractmethod
    def get_board(self):
        """Returns the underlying configured BrainFlow BoardShim instance."""
        pass

    @abstractmethod
    def get_eeg_channels(self) -> List[int]:
        """Returns the list of indices mapping to EEG data channels."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Starts the device data stream."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops the device data stream."""
        pass

    @abstractmethod
    def read_chunk(self, start_sample: int, num_samples: int) -> 'Any':
        """Reads a chunk of data from the device buffer."""
        pass

    @abstractmethod
    def send_eeg_data(self, data: 'Any') -> None:
        """Sends data through the device wrapper."""
        pass
