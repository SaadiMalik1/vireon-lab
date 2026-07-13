"""
OpenBCI Physical Hardware Device Wrappers.
Uses BrainFlow to stream live clinical data from a Cyton or Ganglion board.
"""
from typing import List
import numpy as np
import threading
from vireon.plugins.devices import IDeviceWrapper

try:
    import brainflow
    from brainflow.board_shim import BoardShim, BoardIds, BrainFlowInputParams
    HAS_BRAINFLOW = True
except ImportError:
    HAS_BRAINFLOW = False

class OpenBCICytonWrapper(IDeviceWrapper):
    def __init__(self, serial_port: str = "", **kwargs):
        if not HAS_BRAINFLOW:
            raise RuntimeError(
                "BrainFlow is required to use a physical OpenBCI board. "
                "Install it using: pip install brainflow"
            )
            
        params = BrainFlowInputParams()
        if serial_port:
            params.serial_port = serial_port
            
        self.board_id = BoardIds.CYTON_BOARD
        self.board = BoardShim(self.board_id, params)
        self.ring_buffer = None
        self.lock = threading.Lock()
        self.num_channels = len(BoardShim.get_eeg_channels(self.board_id))

    def get_board(self):
        return self.board

    def get_eeg_channels(self) -> List[int]:
        return BoardShim.get_eeg_channels(self.board_id)

    # Added custom stream management to hide BrainFlow from Coordinator and fix impedance mismatch
    def start_stream(self):
        if not self.board.is_prepared():
            self.board.prepare_session()
        self.board.start_stream()
        self.ring_buffer = np.empty((self.num_channels + 1, 0)) # +1 to safely cover channel indices if they are non-contiguous

    def stop_stream(self):
        if self.board.is_prepared():
            self.board.stop_stream()
            self.board.release_session()
            
    def read_chunk(self, start_sample: int, num_samples: int) -> np.ndarray:
        """
        Pull exactly `num_samples` from the board. 
        If not enough data, return NaNs for the missing parts to maintain time coherence.
        """
        with self.lock:
            # Drain new data from BrainFlow
            new_data = self.board.get_board_data()
            if new_data.size > 0:
                if self.ring_buffer.size == 0:
                    self.ring_buffer = new_data
                else:
                    self.ring_buffer = np.hstack((self.ring_buffer, new_data))
                    
            # Extract exactly num_samples
            max_channel = max(self.get_eeg_channels())
            out = np.full((max_channel + 1, num_samples), np.nan)
            
            available = self.ring_buffer.shape[1] if self.ring_buffer.size > 0 else 0
            take = min(available, num_samples)
            
            if take > 0:
                out[:self.ring_buffer.shape[0], :take] = self.ring_buffer[:, :take]
                self.ring_buffer = self.ring_buffer[:, take:]
                
            return out


class OpenBCIGanglionWrapper(IDeviceWrapper):
    def __init__(self, serial_port: str = "", **kwargs):
        if not HAS_BRAINFLOW:
            raise RuntimeError(
                "BrainFlow is required to use a physical OpenBCI board. "
                "Install it using: pip install brainflow"
            )
            
        params = BrainFlowInputParams()
        if serial_port:
            params.serial_port = serial_port
            
        self.board_id = BoardIds.GANGLION_BOARD
        self.board = BoardShim(self.board_id, params)
        self.ring_buffer = None
        self.lock = threading.Lock()
        self.num_channels = len(BoardShim.get_eeg_channels(self.board_id))

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
