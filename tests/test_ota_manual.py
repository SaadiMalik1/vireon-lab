import struct
import sys
from cryptography.hazmat.primitives.asymmetric import ed25519
from vireon.plugins.firmware.cortex_m_stub import CortexMStub

def test_valid_ota_update():
    stub = CortexMStub()
    payload_version = 2
    header = struct.pack('<I', payload_version)
    firmware_binary = b'ValidFirmwareData' * 10
    private_key = ed25519.Ed25519PrivateKey.generate()
    stub.ota_public_key = private_key.public_key()
    signature = private_key.sign(firmware_binary)
    full_payload = header + signature + firmware_binary
    
    success = stub.process_ota_update(full_payload)
    assert success is True, "Valid OTA failed"
    assert not stub.crashed, "Stub crashed unexpectedly"
    assert stub.efuses["MIN_SVN"] == 2, "SVN not updated"
    print("test_valid_ota_update passed")

def test_rollback_attack_blocked():
    stub = CortexMStub()
    initial_svn = stub.efuses["MIN_SVN"]
    
    payload_version = 0
    header = struct.pack('<I', payload_version)
    malicious_binary = b'MaliciousPayload' * 10
    private_key = ed25519.Ed25519PrivateKey.generate()
    stub.ota_public_key = private_key.public_key()
    signature = private_key.sign(malicious_binary)
    full_payload = header + signature + malicious_binary
    
    success = stub.process_ota_update(full_payload)
    assert success is False, "Rollback attack succeeded!"
    assert stub.crashed is True, "Stub did not crash"
    assert "Anti-Rollback violation" in stub.crash_reason, "Wrong crash reason"
    assert stub.efuses["MIN_SVN"] == initial_svn, "SVN downgraded!"
    print("test_rollback_attack_blocked passed")

if __name__ == '__main__':
    try:
        test_valid_ota_update()
        test_rollback_attack_blocked()
        print("ALL TESTS PASSED")
    except AssertionError as e:
        print("TEST FAILED:", e)
        sys.exit(1)
