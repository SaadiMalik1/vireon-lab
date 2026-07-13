from vireon.core.protocol import RFFrameProcessor, ProtocolError, CryptoEmulator, CertificateError

def test_x509_validation():
    valid_cert = {
        "issuer": "NeuroShield_Root_CA",
        "subject": "Implant_123",
        "valid_from": 0,
        "valid_to": 2e9,
        "public_key": "pubkey_hex",
        "signature": "VALID_ROOT_CA_SIG"
    }
    assert CryptoEmulator.validate_x509_cert(valid_cert) == True
    
    invalid_cert = valid_cert.copy()
    invalid_cert["signature"] = "BAD_SIG"
    try:
        CryptoEmulator.validate_x509_cert(invalid_cert)
        assert False, "Should have raised CertificateError"
    except CertificateError:
        pass

def test_ecdh_key_exchange():
    key_a = b"device_priv_A"
    key_b = b"programmer_pub_B"
    shared_secret_1 = CryptoEmulator.ecdh_key_exchange(key_a, key_b)
    shared_secret_2 = CryptoEmulator.ecdh_key_exchange(key_b, key_a)
    assert shared_secret_1 == shared_secret_2

def test_aes_gcm_emulation():
    processor = RFFrameProcessor()
    processor.derive_session_key(b"salt_123")
    
    payload = b"NEURAL_DATA_BLOCK"
    frame = processor.pack_frame(1, 10, payload, secure_mode=True)
    
    seq_no, payload_type, decoded_payload = processor.unpack_frame(frame, secure_mode=True)
    
    assert seq_no == 1
    assert payload_type == 10
    assert decoded_payload == payload
    
    # Tamper with ciphertext
    tampered_frame = bytearray(frame)
    tampered_frame[20] ^= 0xFF
    try:
        processor.unpack_frame(bytes(tampered_frame), secure_mode=True)
        assert False, "Should have raised ProtocolError"
    except ProtocolError as e:
        assert "AES-GCM Auth Tag verification failed" in str(e)
