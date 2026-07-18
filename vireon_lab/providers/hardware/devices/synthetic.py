import numpy as np
from typing import List, Any
from vireon_lab.providers.devices import IDeviceWrapper

# Graceful check for brainflow
try:
    from brainflow.board_shim import BoardShim, BoardIds, BrainFlowInputParams
    HAS_BRAINFLOW = True
except ImportError:
    HAS_BRAINFLOW = False

    # Mock classes if brainflow is not installed
    class BrainFlowInputParams:  # type: ignore[no-redef]
        def __init__(self):
            self.serial_port = ""
            
    class BoardIds:  # type: ignore[no-redef]
        SYNTHETIC_BOARD = -1
        PIEEG_BOARD = 100 # custom mock id

    class BoardShim:  # type: ignore[no-redef]
        def __init__(self, board_id: int, params: BrainFlowInputParams):
            self.board_id = board_id
            self.params = params
            self._prepared = False
            self._streaming = False
            self.sample_counter = 0

        def prepare_session(self):
            self._prepared = True

        def is_prepared(self) -> bool:
            return self._prepared

        def start_stream(self, num_samples: int = 1200):
            if not self._prepared:
                raise Exception("Session not prepared")
            self._streaming = True

        def stop_stream(self):
            self._streaming = False

        def release_session(self):
            self._prepared = False

        def get_board_data(self) -> np.ndarray:
            if not self._streaming:
                return np.empty((32, 0))
            
            # Brainflow synthetic board returns 32 channels.
            # EEG channels are usually indices 1 to 8.
            num_channels = 32
            num_samples = 25  # corresponding to 100ms at 250Hz
            
            data = np.zeros((num_channels, num_samples))
            # Package counter row (index 0)
            data[0, :] = np.arange(self.sample_counter, self.sample_counter + num_samples)
            self.sample_counter += num_samples
            
            # Generate mock EEG signals on channels 1-8
            t = np.arange(num_samples) / 250.0
            for i in range(1, 9):
                # Sine wave + noise
                data[i, :] = 25.0 * np.sin(2 * np.pi * 10.0 * t + i) + np.random.normal(0, 2.0, num_samples)
                
            return data

        @staticmethod
        def get_eeg_channels(board_id: int) -> List[int]:
            return [1, 2, 3, 4, 5, 6, 7, 8]

class SyntheticBoardWrapper(IDeviceWrapper):
    def __init__(self, **kwargs):
        params = BrainFlowInputParams()
        self.board_id = BoardIds.SYNTHETIC_BOARD
        self.board = BoardShim(self.board_id, params)

    def get_board(self) -> BoardShim:
        return self.board

    def get_eeg_channels(self) -> List[int]:
        if HAS_BRAINFLOW:
            # Using real BoardShim static method
            return BoardShim.get_eeg_channels(self.board_id)
        else:
            return [1, 2, 3, 4, 5, 6, 7, 8]

    def start(self):
        self.board.prepare_session()
        self.board.start_stream()

    def stop(self):
        self.board.stop_stream()
        self.board.release_session()

    def read_chunk(self, start_sample: int = 0, num_samples: int = -1) -> np.ndarray:
        data = self.board.get_board_data()
        channels = self.get_eeg_channels()
        if data.shape[1] > 0:
            return data[channels, :]
        return np.empty((len(channels), 0))

    def send_eeg_data(self, data: Any) -> None:
        pass
