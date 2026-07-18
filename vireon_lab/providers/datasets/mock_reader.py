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


class MockEEGReader(IDatasetReader):
    """
    Generates synthetic neural signals representing EEG bands (Alpha, Beta, Gamma).
    Acts as a fallback when physical files are not available, or for baseline runs.
    """

    def __init__(self, sample_rate: int = 250, num_channels: int = 8):
        self._sample_rate = sample_rate
        self._num_channels = num_channels
        self._channel_names = [f"Ch{i}" for i in range(num_channels)]

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def num_channels(self) -> int:
        return self._num_channels

    @property
    def total_samples(self) -> int:
        return -1  # Infinite stream

    @property
    def duration_sec(self) -> float:
        return -1.0  # Infinite stream

    @property
    def channel_names(self) -> List[str]:
        return self._channel_names

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "subject_id": "synthetic_subject",
            "device_id": "synthetic_generator",
            "type": "synthetic_eeg"
        }

    @property
    def supports_seeking(self) -> bool:
        return True

    def seek(self, sample_position: int) -> None:
        if sample_position < 0:
            raise ValueError("Position must be non-negative")
        # For a synthetic mock, we don't have to keep state,
        # read_chunk determines position via start_sample.

    def read_chunk(self, start_sample: int, num_samples: int) -> np.ndarray:
        t = (start_sample + np.arange(num_samples)) / self._sample_rate
        data = np.zeros((self._num_channels, num_samples))

        for ch in range(self._num_channels):
            # Alpha band (e.g., 10 Hz)
            alpha = 15.0 * np.sin(2 * np.pi * 10.0 * t + ch)
            # Beta band (e.g., 20 Hz)
            beta = 8.0 * np.sin(2 * np.pi * 20.0 * t + 2 * ch)
            # Gamma band (e.g., 40 Hz)
            gamma = 4.0 * np.sin(2 * np.pi * 40.0 * t + 3 * ch)
            # Slow drift / delta band (e.g., 1.5 Hz)
            delta = 20.0 * np.sin(2 * np.pi * 1.5 * t)

            # Combine signals
            data[ch, :] = alpha + beta + gamma + delta

            # Add small ambient noise (1.5 uV RMS)
            data[ch, :] += np.random.normal(0, 1.5, size=num_samples)

        return data
