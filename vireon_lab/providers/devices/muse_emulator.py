import threading
import time
import numpy as np
from typing import List, Any
from vireon.sdk.state import IStateStore as StateStore
from vireon_lab.providers.devices import IDeviceWrapper

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
