import unittest
import numpy as np
import time
from vireon.plugins.devices.pieeg import PiEEGSpiBoard, PiEEGBoardWrapper, HAS_HARDWARE_LIBS

class TestPiEEGHardwareEmulator(unittest.TestCase):
    def setUp(self):
        self.wrapper = PiEEGBoardWrapper()
        self.board = self.wrapper.get_board()

    def tearDown(self):
        self.board.release_session()

    def test_wrapper_channels(self):
        self.assertEqual(self.wrapper.get_eeg_channels(), [1, 2, 3, 4, 5, 6, 7, 8])

    def test_spi_read_cycle(self):
        # 1. Verify initial states
        self.assertFalse(self.board.is_prepared())
        self.assertFalse(self.board._streaming)
        
        # 2. Prepare session
        self.board.prepare_session()
        self.assertTrue(self.board.is_prepared())
        
        # 3. Start stream
        self.board.start_stream()
        self.assertTrue(self.board._streaming)
        
        # 4. Wait for 100ms to accumulate samples (250Hz => ~25 samples)
        time.sleep(0.12)
        
        # 5. Fetch accumulated data
        data = self.board.get_board_data()
        
        # 6. Verify data shape and values
        self.assertEqual(data.shape[0], 32)
        # Should have read approximately 10 to 35 samples
        self.assertGreater(data.shape[1], 5)
        
        # Ensure EEG channel signals (channels 1 to 8) are non-zero and within expected ranges
        for ch in range(1, 9):
            channel_data = data[ch, :]
            # Check variance is non-zero (since we inject synthetic sine + noise)
            self.assertGreater(np.var(channel_data), 0.0)
            # Ensure mean is not completely zero
            self.assertNotEqual(np.mean(channel_data), 0.0)

    def test_stop_release(self):
        self.board.prepare_session()
        self.board.start_stream()
        self.assertTrue(self.board._streaming)
        
        self.board.stop_stream()
        self.assertFalse(self.board._streaming)
        
        self.board.release_session()
        self.assertFalse(self.board.is_prepared())
