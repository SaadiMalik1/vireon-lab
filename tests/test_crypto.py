from vireon.core.protocol import RFFrameProcessor, ProtocolError, CryptoEmulator, CertificateError

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization
import datetime

def generate_test_certs():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"VIREON_Root_CA"),
    ])
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    ).not_valid_after(
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    ).sign(private_key, hashes.SHA256())
    
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    return cert_pem, cert_pem

def test_x509_validation():
    cert_pem, root_pem = generate_test_certs()
    assert CryptoEmulator.validate_x509_cert(cert_pem, root_pem)
    
    invalid_cert = cert_pem.replace(b"CERTIFICATE", b"CERT")
    try:
        CryptoEmulator.validate_x509_cert(invalid_cert, root_pem)
        assert False, "Should have raised CertificateError"
    except CertificateError:
        pass

def generate_ec_keys():
    from cryptography.hazmat.primitives.asymmetric import x25519
    from cryptography.hazmat.primitives import serialization
    priv = x25519.X25519PrivateKey.generate()
    pub = priv.public_key()
    priv_pem = priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    pub_pem = pub.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return priv_pem, pub_pem

def test_ecdh_key_exchange():
    priv_a, pub_a = generate_ec_keys()
    priv_b, pub_b = generate_ec_keys()
    shared_secret_1 = CryptoEmulator.ecdh_key_exchange(priv_a, pub_b)
    shared_secret_2 = CryptoEmulator.ecdh_key_exchange(priv_b, pub_a)
    assert shared_secret_1 == shared_secret_2

def test_aes_gcm_emulation():
    processor = RFFrameProcessor(b"X"*32)
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
