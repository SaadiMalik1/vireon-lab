import numpy as np
import os
from typing import List, Dict, Any, Optional
from vireon.plugins.datasets import IDatasetReader
from vireon.plugins.datasets.mock_reader import MockEEGReader

try:
    import mne
    HAS_MNE = True
except ImportError:
    HAS_MNE = False

class MNEReader(IDatasetReader):
    """
    Universal reader for MNE-supported formats (BrainVision .vhdr, EEGLAB .set, EDF/BDF).
    Falls back gracefully to MockEEGReader if mne is not installed.
    """

    def __init__(self, file_path: str, fallback_on_error: bool = True):
        self.file_path = file_path
        self.fallback_on_error = fallback_on_error
        self.raw = None
        self._sample_rate = 250
        self._num_channels = 8
        self.mock_reader = None

        self._channel_names: List[str] = []
        self._total_samples = 0
        self._duration_sec = 0.0
        self._metadata: Dict[str, Any] = {}

        if not HAS_MNE:
            if fallback_on_error:
                print(f"[MNEReader] mne-python not installed. Falling back to MockEEGReader.")
                self.mock_reader = MockEEGReader(self._sample_rate, self._num_channels)
            else:
                raise ImportError("mne is required to read these files but was not found.")
        else:
            try:
                ext = os.path.splitext(file_path)[1].lower()
                if ext == '.vhdr':
                    self.raw = mne.io.read_raw_brainvision(file_path, preload=False, verbose=False)
                elif ext == '.set':
                    self.raw = mne.io.read_raw_eeglab(file_path, preload=False, verbose=False)
                elif ext in ('.edf', '.bdf'):
                    self.raw = mne.io.read_raw_edf(file_path, preload=False, verbose=False)
                else:
                    self.raw = mne.io.read_raw(file_path, preload=False, verbose=False)
                
                self._sample_rate = int(self.raw.info["sfreq"])
                self._num_channels = len(self.raw.ch_names)
                self._total_samples = self.raw.n_times
                self._duration_sec = float(self.raw.times[-1])
                self._channel_names = list(self.raw.ch_names)

                self._metadata = {
                    "file_path": file_path,
                    "subject_id": str(self.raw.info.get("subject_info", "unknown")),
                    "device_id": str(self.raw.info.get("device_info", "unknown")),
                    "duration_sec": self._duration_sec,
                    "total_samples": self._total_samples,
                    "sfreq": self._sample_rate,
                }
            except Exception as e:
                if fallback_on_error:
                    print(f"[MNEReader] Error reading {file_path}: {e}. Falling back to MockEEGReader.")
                    self.mock_reader = MockEEGReader(self._sample_rate, self._num_channels)
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
        return self._total_samples

    @property
    def duration_sec(self) -> float:
        if self.mock_reader:
            return self.mock_reader.duration_sec
        return self._duration_sec

    @property
    def channel_names(self) -> List[str]:
        if self.mock_reader:
            return self.mock_reader.channel_names
        return self._channel_names

    @property
    def metadata(self) -> Dict[str, Any]:
        if self.mock_reader:
            return self.mock_reader.metadata
        return self._metadata

    @property
    def supports_seeking(self) -> bool:
        return True

    def seek(self, sample_position: int) -> None:
        if self.mock_reader:
            self.mock_reader.seek(sample_position)
            return

        if sample_position < 0 or sample_position >= self._total_samples:
            raise ValueError(f"Sample position {sample_position} out of bounds")

    def read_chunk(self, start_sample: int, num_samples: int) -> np.ndarray:
        if self.mock_reader:
            return self.mock_reader.read_chunk(start_sample, num_samples)

        if self.raw is None:
            return np.zeros((self._num_channels, num_samples))

        try:
            start = start_sample % self._total_samples
            stop = start + num_samples

            if stop <= self._total_samples:
                data, _ = self.raw[:, start:stop]
            else:
                data_part1, _ = self.raw[:, start:self._total_samples]
                data_part2, _ = self.raw[:, 0:stop - self._total_samples]
                data = np.concatenate((data_part1, data_part2), axis=1)

            return data * 1e6
        except Exception:
            return np.zeros((self._num_channels, num_samples))
