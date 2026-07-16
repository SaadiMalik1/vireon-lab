import numpy as np
from typing import List
from vireon.plugins.devices import IDeviceWrapper

try:
    from pylsl import resolve_stream, StreamInlet
    HAS_LSL = True
except (ImportError, RuntimeError) as e:
    HAS_LSL = False
    print(f"[LSLBridge] pylsl not available or missing binary: {e}")

class _LSLBoardShimMock:
    """Mocks the brainflow.board_shim API used by ReplayEngine."""
    def __init__(self, stream_name: str, max_channels: int):
        self.stream_name = stream_name
        self.max_channels = max_channels
        self.inlet = None
        self.prepared = False
        self.streaming = False
        self._eeg_channels = list(range(max_channels))

    def is_prepared(self) -> bool:
        return self.prepared

    def prepare_session(self):
        if not HAS_LSL:
            raise ImportError("pylsl is not installed. Cannot use LSLBridge.")
        
        print(f"[LSLBridge] Resolving stream '{self.stream_name}'...")
        streams = resolve_stream('name', self.stream_name)
        if not streams:
            raise RuntimeError(f"Could not find LSL stream named '{self.stream_name}'")
        
        self.inlet = StreamInlet(streams[0])
        info = self.inlet.info()
        ch_count = info.channel_count()
        self._eeg_channels = list(range(ch_count))
        self.prepared = True
        print(f"[LSLBridge] Connected to LSL stream '{self.stream_name}' ({ch_count} channels)")

    def start_stream(self):
        if not self.prepared:
            raise RuntimeError("Cannot start stream without preparing session.")
        self.streaming = True

    def get_board_data(self) -> np.ndarray:
        if not self.streaming or not self.inlet:
            return np.zeros((len(self._eeg_channels), 0))
            
        chunk, timestamps = self.inlet.pull_chunk()
        if not chunk:
            return np.zeros((len(self._eeg_channels), 0))
            
        # chunk is a list of lists: (samples, channels)
        data = np.array(chunk).T
        return data

    def stop_stream(self):
        self.streaming = False

    def release_session(self):
        if self.inlet:
            self.inlet.close_stream()
        self.prepared = False

class LSLDeviceWrapper(IDeviceWrapper):
    """
    Device wrapper that acts as an LSL Inlet.
    Connects to an existing LSL stream and pulls chunks as if from hardware.
    """
    def __init__(self, stream_name: str = 'VIREON_EEG', max_channels: int = 8):
        self.board_mock = _LSLBoardShimMock(stream_name, max_channels)

    def get_board(self):
        """Returns the mock board."""
        return self.board_mock

    def get_eeg_channels(self) -> List[int]:
        return self.board_mock._eeg_channels
