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
from typing import List, Dict, Any
from vireon_lab.providers.datasets import IDatasetReader
from vireon_lab.providers.datasets.mock_reader import MockEEGReader

try:
    import mne
    HAS_MNE = True
except ImportError:
    HAS_MNE = False


class FIFReader(IDatasetReader):
    """
    Reader for MNE Functional Imaging File (.fif) format.
    Falls back gracefully to MockEEGReader if mne is not installed
    or if the file is missing/invalid.
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
                print("[FIFReader] mne-python not installed. Falling back to MockEEGReader.")
                self.mock_reader = MockEEGReader(self._sample_rate, self._num_channels)
            else:
                raise ImportError("mne is required to read FIF files but was not found.")
        else:
            try:
                # Read FIF file raw info (don't preload all unless requested)
                self.raw = mne.io.read_raw_fif(file_path, preload=False, verbose=False)
                self._sample_rate = int(self.raw.info["sfreq"])
                self._num_channels = len(self.raw.ch_names)
                self._total_samples = self.raw.n_times
                self._duration_sec = float(self.raw.times[-1])
                self._channel_names = list(self.raw.ch_names)

                # Extract rich metadata
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
                    print(f"[FIFReader] Error reading {file_path}: {e}. Falling back to MockEEGReader.")
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
            raise ValueError(f"Sample position {sample_position} out of bounds for total_samples {self._total_samples}")

    def read_chunk(self, start_sample: int, num_samples: int) -> np.ndarray:
        if self.mock_reader:
            return self.mock_reader.read_chunk(start_sample, num_samples)

        if self.raw is None:
            return np.zeros((self._num_channels, num_samples))

        try:
            # Wrap around if start_sample exceeds total length
            start = start_sample % self._total_samples
            stop = start + num_samples

            if stop <= self._total_samples:
                data, _ = self.raw[:, start:stop]
            else:
                # Wrap read across boundaries
                data_part1, _ = self.raw[:, start:self._total_samples]
                data_part2, _ = self.raw[:, 0:stop - self._total_samples]
                data = np.concatenate((data_part1, data_part2), axis=1)

            # MNE data is standard in Volts, convert to microvolts for consistency (1V = 1e6 uV)
            return data * 1e6
        except Exception:
            return np.zeros((self._num_channels, num_samples))
