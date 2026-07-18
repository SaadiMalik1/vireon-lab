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

import unittest
import socket
import time
import numpy as np
from vireon_lab.providers.devices.hardware_bridge import HardwareBridge

def pack_24bit(val: int) -> bytes:
    val = int(val)
    if val < 0:
        val += 16777216
    return bytes([(val >> 16) & 0xFF, (val >> 8) & 0xFF, val & 0xFF])

class TestHardwareBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = HardwareBridge(host="127.0.0.1", port=9191, num_channels=8)
        self.bridge.start()
        time.sleep(0.1) # Wait for socket thread to bind

    def tearDown(self):
        self.bridge.stop()

    def test_bridge_socket_reconstruction(self):
        # 1. Connect test client to bridge
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", 9191))
        
        # 2. Build standard 33-byte frame
        # We will encode channel 0 with value 100000 counts, and channel 1 with -50000 counts
        packet = bytearray()
        packet.append(0xA0) # Header
        packet.append(42)   # Sample index
        
        # Ch 0
        packet.extend(pack_24bit(100000))
        # Ch 1
        packet.extend(pack_24bit(-50000))
        # Ch 2 to 7 (zeros)
        for _ in range(6):
            packet.extend(pack_24bit(0))
            
        packet.extend(bytes([0, 0, 0, 0, 0, 0])) # AUX
        packet.append(0xC0)                      # Footer
        
        # Transmit packet
        client.sendall(packet)
        time.sleep(0.1) # Wait for bridge parsing
        
        # Read from bridge
        chunk = self.bridge.read_chunk(1)
        self.assertEqual(chunk.shape, (8, 1))
        
        # Verify scaling and values
        expected_ch0 = 100000 * 0.02235174
        expected_ch1 = -50000 * 0.02235174
        
        self.assertAlmostEqual(chunk[0, 0], expected_ch0, places=2)
        self.assertAlmostEqual(chunk[1, 0], expected_ch1, places=2)
        self.assertAlmostEqual(chunk[2, 0], 0.0, places=2)
        
        client.close()

    def test_alignment_recovery(self):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", 9191))
        
        # Send garbage bytes to test recovery alignment
        client.sendall(b"garbage_header_bytes_without_sync")
        
        # Send valid packet
        packet = bytearray()
        packet.append(0xA0) # Header
        packet.append(10)   # Index
        for _ in range(8):
            packet.extend(pack_24bit(12345))
        packet.extend(bytes([0]*6)) # AUX
        packet.append(0xC0) # Footer
        
        client.sendall(packet)
        time.sleep(0.1)
        
        # Read from bridge
        chunk = self.bridge.read_chunk(1)
        self.assertEqual(chunk.shape, (8, 1))
        self.assertAlmostEqual(chunk[0, 0], 12345 * 0.02235174, places=2)
        
        client.close()

    def test_buffer_starvation(self):
        # Read from starving buffer
        chunk = self.bridge.read_chunk(5)
        self.assertEqual(chunk.shape, (8, 5))
        
        # Remainder should fill with nominal noise
        self.assertNotEqual(np.sum(chunk), 0.0)

if __name__ == "__main__":
    unittest.main()
