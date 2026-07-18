import os
import numpy as np
from typing import List, Dict, Any, Optional
from vireon.plugins.datasets import IDatasetReader
from vireon.plugins.datasets.mock_reader import MockEEGReader


class CSVReader(IDatasetReader):
    """
    Reads neural signals from a CSV file.
    Expects columns to represent EEG channels, and rows to represent samples.
    """

    def __init__(self, file_path: str, sample_rate: int = 250, fallback_on_error: bool = True):
        self.file_path = file_path
        self.fallback_on_error = fallback_on_error
        self._sample_rate = sample_rate
        self.data: Optional[np.ndarray] = None
        self.mock_reader = None
        self._num_channels = 8
        self._channel_names: List[str] = []

        if not os.path.exists(file_path):
            if fallback_on_error:
                print(f"[CSVReader] File {file_path} not found. Falling back to MockEEGReader.")
                self.mock_reader = MockEEGReader(sample_rate, 8)
            else:
                raise FileNotFoundError(f"CSV file not found: {file_path}")
        else:
            try:
                # Load CSV using numpy
                # Delimiter can be comma, tab, or space
                raw_data = np.loadtxt(file_path, delimiter=",")
                # If 1D, reshape to (samples, 1)
                if len(raw_data.shape) == 1:
                    raw_data = raw_data.reshape(-1, 1)
                # We want channels x samples, so transpose
                self.data = raw_data.T
                self._num_channels = self.data.shape[0]
                self._channel_names = [f"EEG{i}" for i in range(self._num_channels)]
            except Exception as e:
                if fallback_on_error:
                    print(f"[CSVReader] Error loading CSV: {e}. Falling back to MockEEGReader.")
                    self.mock_reader = MockEEGReader(sample_rate, 8)
                else:
                    raise e

    @property
    def sample_rate(self) -> int:
        if self.mock_reader:
            return self.mock_reader.sample_rate
        return self._sample_rate

    @property
    def num_channels(self) -> int:
        if self.mock_reader:
            return self.mock_reader.num_channels
        return self._num_channels

    @property
    def total_samples(self) -> int:
        if self.mock_reader:
            return self.mock_reader.total_samples
        return self.data.shape[1] if self.data is not None else 0

    @property
    def duration_sec(self) -> float:
        if self.mock_reader:
            return self.mock_reader.duration_sec
        return (self.data.shape[1] / self._sample_rate) if self.data is not None else 0.0

    @property
    def channel_names(self) -> List[str]:
        if self.mock_reader:
            return self.mock_reader.channel_names
        return self._channel_names

    @property
    def metadata(self) -> Dict[str, Any]:
        if self.mock_reader:
            return self.mock_reader.metadata
        return {
            "file_path": self.file_path,
            "type": "csv_recording",
            "duration_sec": self.duration_sec,
            "total_samples": self.total_samples,
        }

    @property
    def supports_seeking(self) -> bool:
        return True

    def seek(self, sample_position: int) -> None:
        if self.mock_reader:
            self.mock_reader.seek(sample_position)
            return

        if sample_position < 0 or (self.data is not None and sample_position >= self.data.shape[1]):
            raise ValueError("Seek position out of bounds")

    def read_chunk(self, start_sample: int, num_samples: int) -> np.ndarray:
        if self.mock_reader:
            return self.mock_reader.read_chunk(start_sample, num_samples)

        if self.data is None:
            return np.zeros((self._num_channels, num_samples))

        total_samples = self.data.shape[1]

        # Determine read indices, wrap if reaching end of data
        indices = np.arange(start_sample, start_sample + num_samples) % total_samples
        return self.data[:, indices]
