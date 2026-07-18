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

"""
OpenBCI Physical Hardware Device Wrappers.
Uses BrainFlow to stream live clinical data from a Cyton or Ganglion board.
"""
from typing import List
import numpy as np
import threading
from vireon_lab.providers.hardware.devices import IDeviceWrapper

try:
    from brainflow.board_shim import BoardShim, BoardIds, BrainFlowInputParams
    HAS_BRAINFLOW = True
except ImportError:
    HAS_BRAINFLOW = False

class BaseOpenBCIWrapper(IDeviceWrapper):
    def __init__(self, board_id: int, serial_port: str = "", **kwargs):
        if not HAS_BRAINFLOW:
            raise RuntimeError(
                "BrainFlow is required to use a physical OpenBCI board. "
                "Install it using: pip install brainflow"
            )
            
        params = BrainFlowInputParams()
        if serial_port:
            params.serial_port = serial_port
            
        self.board_id = board_id
        self.board = BoardShim(self.board_id, params)
        self.num_channels = len(BoardShim.get_eeg_channels(self.board_id))
        self.ring_buffer: np.ndarray = np.empty((self.num_channels + 1, 0))
        self.lock = threading.Lock()

    def get_board(self):
        return self.board

    def get_eeg_channels(self) -> List[int]:
        return BoardShim.get_eeg_channels(self.board_id)

    def start_stream(self):
        if not self.board.is_prepared():
            self.board.prepare_session()
        self.board.start_stream()
        self.ring_buffer = np.empty((self.num_channels + 1, 0))

    def stop_stream(self):
        if self.board.is_prepared():
            self.board.stop_stream()
            self.board.release_session()
            
    def read_chunk(self, start_sample: int, num_samples: int) -> np.ndarray:
        with self.lock:
            new_data = self.board.get_board_data()
            if new_data.size > 0:
                if self.ring_buffer.size == 0:
                    self.ring_buffer = new_data
                else:
                    self.ring_buffer = np.hstack((self.ring_buffer, new_data))
                    
            max_channel = max(self.get_eeg_channels())
            out = np.full((max_channel + 1, num_samples), np.nan)
            
            available = self.ring_buffer.shape[1] if self.ring_buffer.size > 0 else 0
            take = min(available, num_samples)
            
            if take > 0:
                out[:self.ring_buffer.shape[0], :take] = self.ring_buffer[:, :take]
                self.ring_buffer = self.ring_buffer[:, take:]
                
            return out


class OpenBCICytonWrapper(BaseOpenBCIWrapper):
    def __init__(self, serial_port: str = "", **kwargs):
        super().__init__(BoardIds.CYTON_BOARD, serial_port=serial_port, **kwargs)


class OpenBCIGanglionWrapper(BaseOpenBCIWrapper):
    def __init__(self, serial_port: str = "", **kwargs):
        super().__init__(BoardIds.GANGLION_BOARD, serial_port=serial_port, **kwargs)
