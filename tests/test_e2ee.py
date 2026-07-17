import pytest
import time
from vireon.core.e2ee import E2EEChannel

def test_e2ee_channel_establish_session():
    channel = E2EEChannel()
    assert channel.session_key is None
    
    success = channel.establish_session()
    assert success is True
    assert channel.session_key is not None
    assert len(channel.session_key) == 32 # AES-GCM 256
    assert channel.packets_since_rotation == 0

def test_e2ee_channel_encrypt_decrypt():
    channel = E2EEChannel()
    data = {"sensor": "eeg", "value": 42}
    
    # encrypt_payload should establish session if none exists
    encrypted = channel.encrypt_payload(data)
    assert isinstance(encrypted, str)
    assert channel.session_key is not None
    assert channel.packets_since_rotation == 1
    
    # Decrypt
    decrypted = channel.decrypt_payload(encrypted)
    assert decrypted == data

def test_e2ee_channel_rotation_by_packets():
    channel = E2EEChannel()
    channel.establish_session()
    
    old_key = channel.session_key
    channel.packets_since_rotation = 100001
    
    # Next encryption should trigger rotation
    channel.encrypt_payload({"test": "data"})
    assert channel.session_key != old_key
    assert channel.packets_since_rotation == 1 # 0 then +1 after encrypt

def test_e2ee_channel_rotation_by_time():
    channel = E2EEChannel(key_rotation_interval_sec=0.1)
    channel.establish_session()
    old_key = channel.session_key
    
    # Wait for interval to expire
    time.sleep(0.15)
    
    # Next encryption should trigger rotation
    channel.encrypt_payload({"test": "data"})
    assert channel.session_key != old_key

def test_e2ee_channel_decrypt_without_session():
    channel = E2EEChannel()
    with pytest.raises(ValueError, match="No session key established"):
        channel.decrypt_payload("invalid")

def test_e2ee_channel_decrypt_invalid_payload():
    channel = E2EEChannel()
    channel.establish_session()
    with pytest.raises(ValueError, match="Invalid AES-GCM payload size"):
        channel.decrypt_payload("abcd") # too short

def test_e2ee_channel_decrypt_auth_failure():
    channel = E2EEChannel()
    data = {"test": "data"}
    encrypted = channel.encrypt_payload(data)
    
    import base64
    raw = bytearray(base64.b64decode(encrypted))
    # Corrupt ciphertext byte
    raw[-1] ^= 0xFF
    corrupted_b64 = base64.b64encode(raw).decode('utf-8')
    
    with pytest.raises(ValueError, match="AES-GCM Auth Tag verification failed"):
        channel.decrypt_payload(corrupted_b64)
