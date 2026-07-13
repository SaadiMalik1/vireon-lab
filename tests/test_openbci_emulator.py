import unittest
import numpy as np
import time
import os
from vireon.core.twin import DigitalTwin
from vireon.plugins.devices.openbci_emulator import OpenBCICytonEmulator

class TestOpenBCICytonEmulator(unittest.TestCase):
    def setUp(self):
        self.twin = DigitalTwin(num_channels=8)
        self.emulator = OpenBCICytonEmulator(self.twin)

    def tearDown(self):
        self.emulator.stop()

    def test_start_stop(self):
        self.emulator.start()
        self.assertTrue(self.emulator.running)
        self.assertIsNotNone(self.emulator.slave_name)
        self.assertTrue(os.path.exists(self.emulator.slave_name))
        
        self.emulator.stop()
        self.assertFalse(self.emulator.running)

    def test_command_handling(self):
        self.emulator.start()
        
        # Open the slave port from the client perspective
        client_fd = os.open(self.emulator.slave_name, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            # Write 'v' command to reset/query board info
            os.write(client_fd, b'v')
            
            # Read response in a loop until we see $$$ or timeout
            response = b""
            start = time.time()
            while b"$$$" not in response and time.time() - start < 1.0:
                try:
                    chunk = os.read(client_fd, 1024)
                    if chunk:
                        response += chunk
                except BlockingIOError:
                    time.sleep(0.01)
            
            self.assertIn(b"OpenBCI V3 8-channel", response)
            self.assertIn(b"$$$", response)
            
            # Verify initial streaming state is False
            self.assertFalse(self.emulator.streaming)
            
            # Write 'b' command to start streaming
            os.write(client_fd, b'b')
            time.sleep(0.05)
            self.assertTrue(self.emulator.streaming)
            
            # Write 's' command to stop streaming
            os.write(client_fd, b's')
            time.sleep(0.05)
            self.assertFalse(self.emulator.streaming)
            
        finally:
            os.close(client_fd)

    def test_data_serialization(self):
        self.emulator.start()
        
        # Open client port
        client_fd = os.open(self.emulator.slave_name, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            # Enable streaming
            os.write(client_fd, b'b')
            time.sleep(0.05)
            self.assertTrue(self.emulator.streaming)
            
            # Generate dummy EEG data: shape (8, 2)
            # Channel 0: 10 uV, Channel 1: -10 uV, others 0
            data = np.zeros((8, 2))
            data[0, :] = 10.0
            data[1, :] = -10.0
            
            eeg_channels = [0, 1, 2, 3, 4, 5, 6, 7]
            self.emulator.send_eeg_data(data, eeg_channels, 250)
            
            # Read packets from client side in a loop
            packets = b""
            start = time.time()
            while len(packets) < 66 and time.time() - start < 1.0:
                try:
                    chunk = os.read(client_fd, 1024)
                    if chunk:
                        packets += chunk
                except BlockingIOError:
                    time.sleep(0.01)
            
            # Since we generated 2 samples, we expect exactly 2 packets of 33 bytes = 66 bytes
            self.assertEqual(len(packets), 66)
            
            # Inspect first packet (first 33 bytes)
            self.assertEqual(packets[0], 0xA0)  # Start byte
            self.assertEqual(packets[1], 0)     # Sample number (starts at 0)
            
            # Channel 0 (10uV) => count = 10 / 0.02235174 = 447 => 0x0001BF
            self.assertEqual(packets[2], 0x00)
            self.assertEqual(packets[3], 0x01)
            self.assertEqual(packets[4], 0xBF)
            
            # Channel 1 (-10uV) => count = -447 => (1 << 24) - 447 = 16776769 => 0xFFFE41
            self.assertEqual(packets[5], 0xFF)
            self.assertEqual(packets[6], 0xFE)
            self.assertEqual(packets[7], 0x41)
            
            # Stop byte
            self.assertEqual(packets[32], 0xC0)
            
            # Inspect second packet (next 33 bytes)
            self.assertEqual(packets[33], 0xA0)
            self.assertEqual(packets[34], 1)     # Sample number increments
            self.assertEqual(packets[65], 0xC0)  # Stop byte
            
        finally:
            os.close(client_fd)

if __name__ == "__main__":
    unittest.main()
