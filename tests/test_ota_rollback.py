import unittest
import struct
from vireon.plugins.firmware.cortex_m_stub import CortexMStub

class TestOTARollback(unittest.TestCase):
    def test_valid_ota_update(self):
        """Test that an OTA update with a valid/newer SVN succeeds and updates the efuse."""
        stub = CortexMStub()
        
        # SVN is 2, higher than MIN_SVN (1)
        payload_version = 2
        header = struct.pack('<I', payload_version)
        firmware_binary = b'ValidFirmwareData' * 10
        full_payload = header + firmware_binary
        
        success = stub.process_ota_update(full_payload)
        
        self.assertTrue(success)
        self.assertFalse(stub.crashed)
        self.assertEqual(stub.efuses["MIN_SVN"], 2)
        
        # Verify memory was actually written
        read_back = stub.flash[:len(firmware_binary)]
        self.assertEqual(read_back, firmware_binary)

    def test_rollback_attack_blocked(self):
        """Test that an OTA update with an older SVN fails due to anti-rollback protections."""
        stub = CortexMStub()
        initial_svn = stub.efuses["MIN_SVN"] # defaults to 1
        
        # SVN is 0, lower than MIN_SVN (1) -> Rollback Attack
        payload_version = 0
        header = struct.pack('<I', payload_version)
        malicious_binary = b'MaliciousPayload' * 10
        full_payload = header + malicious_binary
        
        success = stub.process_ota_update(full_payload)
        
        self.assertFalse(success)
        self.assertTrue(stub.crashed)
        self.assertIn("Anti-Rollback violation", stub.crash_reason)
        self.assertEqual(stub.efuses["MIN_SVN"], initial_svn)

    def test_ota_payload_too_short(self):
        """Test that a malformed (too short) OTA payload is rejected."""
        stub = CortexMStub()
        
        success = stub.process_ota_update(b'A')
        
        self.assertFalse(success)
        self.assertTrue(stub.crashed)
        self.assertIn("too short to contain header", stub.crash_reason)

if __name__ == '__main__':
    unittest.main()
