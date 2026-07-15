import numpy as np
from typing import Protocol, List

class IDataProvider(Protocol):
    """
    Unified interface for providing EEG signal chunks to the ReplayEngine.
    Abstracts whether data comes from a file (DatasetReader) or physical hardware (DeviceWrapper).
    """
    def read_chunk(self, position: int, num_samples: int) -> np.ndarray:
        """
        Read a chunk of data.
        - Dataset providers should read from `position`.
        - Device providers should ignore `position` and read the latest stream data.
        """
        ...

    def get_eeg_channels(self) -> List[int]:
        """
        Return the list of channel indices that contain EEG data.
        """
        ...


class DatasetProviderAdapter(IDataProvider):
    def __init__(self, dataset_reader):
        self.reader = dataset_reader

    def read_chunk(self, position: int, num_samples: int) -> np.ndarray:
        return self.reader.read_chunk(position, num_samples)

    def get_eeg_channels(self) -> List[int]:
        return list(range(self.reader.num_channels))


class DeviceProviderAdapter(IDataProvider):
    def __init__(self, device_wrapper):
        self.device = device_wrapper
        self.board = self.device.get_board()
        self.eeg_channels = self.device.get_eeg_channels()

    def read_chunk(self, position: int, num_samples: int) -> np.ndarray:
        try:
            if hasattr(self.device, "read_chunk"):
                return self.device.read_chunk(0, num_samples)
            if self.board is not None:
                data_chunk = self.board.get_board_data()
                if data_chunk.size > 0:
                    return data_chunk
            # Fallback
            return np.full((max(self.eeg_channels) + 1, num_samples), np.nan)
        except Exception as e:
            import logging
            logging.error(f"Device read failed: {e}")
            raise RuntimeError(f"Device read failed: {e}")

    def get_eeg_channels(self) -> List[int]:
        return self.eeg_channels
