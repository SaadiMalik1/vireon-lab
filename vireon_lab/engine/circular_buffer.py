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

import threading
import numpy as np
from vireon_lab.engine.interfaces import ICircularBuffer

class CircularBuffer(ICircularBuffer):
    """
    High-performance O(1) thread-safe circular ring buffer.
    Uses modulo write-pointer indexing to eliminate expensive np.roll() memory allocation.
    """
    def __init__(self, num_channels: int, capacity_samples: int):
        self.num_channels = num_channels
        self.capacity = capacity_samples
        self.buffer = np.zeros((num_channels, capacity_samples), dtype=np.float64)
        self.write_pos = 0
        self.total_written = 0
        self._lock = threading.RLock()

    def write(self, data: np.ndarray):
        """
        Writes data matrix of shape (num_channels, step_samples) to the buffer.
        """
        with self._lock:
            num_channels, step_samples = data.shape
            if step_samples > self.capacity:
                data = data[:, -self.capacity:]
                step_samples = self.capacity

            # Calculate split write indices around circular boundary
            space_to_end = self.capacity - self.write_pos
            if step_samples <= space_to_end:
                self.buffer[:, self.write_pos:self.write_pos + step_samples] = data
                self.write_pos = (self.write_pos + step_samples) % self.capacity
            else:
                self.buffer[:, self.write_pos:] = data[:, :space_to_end]
                remainder = step_samples - space_to_end
                self.buffer[:, :remainder] = data[:, space_to_end:]
                self.write_pos = remainder

            self.total_written += step_samples

    def read_last(self, num_samples: int) -> np.ndarray:
        """
        Reads the most recent num_samples in correct chronological order in O(1) time.
        """
        with self._lock:
            samples_to_read = min(num_samples, self.capacity, self.total_written)
            if samples_to_read == 0:
                return np.zeros((self.num_channels, 0))

            start_pos = (self.write_pos - samples_to_read) % self.capacity
            if start_pos < self.write_pos:
                return self.buffer[:, start_pos:self.write_pos].copy()
            else:
                part1 = self.buffer[:, start_pos:]
                part2 = self.buffer[:, :self.write_pos]
                return np.hstack((part1, part2))

    def reset(self):
        """Resets buffer to zero state."""
        with self._lock:
            self.buffer.fill(0.0)
            self.write_pos = 0
            self.total_written = 0
