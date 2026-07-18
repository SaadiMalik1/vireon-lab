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
import time
import numpy as np
from typing import List, Any
from vireon_lab.providers.devices import IDeviceWrapper
from vireon.core.twin import DigitalTwin

class MuseEmulator(IDeviceWrapper):
    """
    Simulates a 4-channel Interaxon Muse headset (TP9, AF7, AF8, TP10) 
    operating at 256 Hz over virtual BLE.
    """
    def __init__(self, twin: DigitalTwin, serial_port: str = ""):
        self.twin = twin
        self.serial_port = serial_port
        self.running = False
        self.thread = None
        self.sample_rate = 256
        self.num_channels = 4
        self.channel_names = ["TP9", "AF7", "AF8", "TP10"]
        self.packet_counter = 0

    def get_board(self) -> Any:
        return None  # Replace with actual board object if needed
        
    def get_eeg_channels(self) -> List[int]:
        return list(range(4))

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.thread.start()
        print("[MuseEmulator] Started virtual Muse 4-channel stream at 256Hz")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        print("[MuseEmulator] Stopped virtual stream")

    def read_chunk(self, start_sample: int, num_samples: int) -> np.ndarray:
        return np.zeros((self.num_channels, num_samples))

    def send_eeg_data(self, state_dict: dict):
        pass # Optional bridge callback

    def _stream_loop(self):
        interval = 1.0 / self.sample_rate
        while self.running:
            start_t = time.time()
            
            # Read state from twin
            state = self.twin.get_state()
            _eeg_data = state["cortical_lfp"][:self.num_channels]
            
            # Form Muse packet (Timestamp, PacketId, TP9, AF7, AF8, TP10)
            self.packet_counter = (self.packet_counter + 1) % 65536
            
            elapsed = time.time() - start_t
            if elapsed < interval:
                time.sleep(interval - elapsed)
