import threading
import time
import numpy as np
from vireon.core.twin import DigitalTwin
from vireon.plugins.devices import IDeviceWrapper

class EmotivEpocEmulator(IDeviceWrapper):
    """
    Simulates a 14-channel Emotiv Epoc+ headset 
    (AF3, F7, F3, FC5, T7, P7, O1, O2, P8, T8, FC6, F4, F8, AF4)
    operating at 128 Hz.
    """
    def __init__(self, twin: DigitalTwin, serial_port: str = ""):
        self.twin = twin
        self.serial_port = serial_port
        self.running = False
        self.thread = None
        self.sample_rate = 128
        self.num_channels = 14
        self.channel_names = ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1", "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"]
        self.packet_counter = 0

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.thread.start()
        print("[EmotivEpocEmulator] Started virtual Emotiv Epoc+ 14-channel stream at 128Hz")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        print("[EmotivEpocEmulator] Stopped virtual stream")

    def send_eeg_data(self, state_dict: dict):
        pass # Optional bridge callback

    def _stream_loop(self):
        interval = 1.0 / self.sample_rate
        while self.running:
            start_t = time.time()
            
            state = self.twin.get_state()
            # If twin doesn't have 14 channels, pad or truncate
            base_eeg = state["cortical_lfp"]
            if len(base_eeg) < self.num_channels:
                eeg_data = np.pad(base_eeg, (0, self.num_channels - len(base_eeg)), mode='reflect')
            else:
                eeg_data = base_eeg[:self.num_channels]
            
            self.packet_counter = (self.packet_counter + 1) % 128
            
            elapsed = time.time() - start_t
            if elapsed < interval:
                time.sleep(interval - elapsed)
