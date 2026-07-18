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
