import pytest
import struct
from vireon.plugins.firmware.cortex_m_stub import CortexMStub
from vireon.core.twin import DigitalTwin

def test_valid_ota_update():
    """Test that an OTA update with a valid/newer SVN succeeds and updates the efuse."""
    stub = CortexMStub()
    initial_svn = stub.efuses["MIN_SVN"]
    
    # SVN is 2, higher than MIN_SVN (1)
    payload_version = 2
    header = struct.pack('<I', payload_version)
    firmware_binary = b'ValidFirmwareData' * 10
    full_payload = header + firmware_binary
    
    success = stub.process_ota_update(full_payload)
    
    assert success is True
    assert not stub.crashed
    assert stub.efuses["MIN_SVN"] == 2
    
    # Verify memory was actually written
    read_back = stub.read_memory(stub.FLASH_BASE, len(firmware_binary))
    assert read_back == firmware_binary

def test_rollback_attack_blocked():
    """Test that an OTA update with an older SVN fails due to anti-rollback protections."""
    stub = CortexMStub()
    initial_svn = stub.efuses["MIN_SVN"] # defaults to 1
    
    # SVN is 0, lower than MIN_SVN (1) -> Rollback Attack
    payload_version = 0
    header = struct.pack('<I', payload_version)
    malicious_binary = b'MaliciousPayload' * 10
    full_payload = header + malicious_binary
    
    success = stub.process_ota_update(full_payload)
    
    assert success is False
    assert stub.crashed is True
    assert "Anti-Rollback violation" in stub.crash_reason
    assert stub.efuses["MIN_SVN"] == initial_svn

def test_ota_payload_too_short():
    """Test that a malformed (too short) OTA payload is rejected."""
    stub = CortexMStub()
    
    success = stub.process_ota_update(b'A')
    
    assert success is False
    assert stub.crashed is True
    assert "too short to contain header" in stub.crash_reason
