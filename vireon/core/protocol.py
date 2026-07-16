import struct
import hmac
import hashlib
from typing import Tuple

class ProtocolError(Exception):
    """Raised when frame validation fails."""
    pass

class CertificateError(ProtocolError):
    """Raised when X.509 validation fails."""
    pass

class CryptoEmulator:
    """Emulates NIST/FIPS compliant cryptography (X.509, ECDH, AES-GCM)."""
    
    @staticmethod
    def validate_x509_cert(pem_cert: bytes, root_ca_pem: bytes) -> bool:
        """Validates an X.509 certificate against a trusted root CA."""
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.exceptions import InvalidSignature
        import datetime

        try:
            cert = x509.load_pem_x509_certificate(pem_cert, default_backend())
            root_cert = x509.load_pem_x509_certificate(root_ca_pem, default_backend())
            
            now = datetime.datetime.now(datetime.timezone.utc)
            if cert.not_valid_after_utc < now or cert.not_valid_before_utc > now:
                raise CertificateError("Invalid X.509 Certificate: Expired or not yet valid.")
                
            from cryptography.hazmat.primitives.asymmetric import rsa, ec
            root_pubkey = root_cert.public_key()
            if isinstance(root_pubkey, rsa.RSAPublicKey):
                root_pubkey.verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    padding.PKCS1v15(),
                    cert.signature_hash_algorithm,
                )
            elif isinstance(root_pubkey, ec.EllipticCurvePublicKey):
                root_pubkey.verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    ec.ECDSA(cert.signature_hash_algorithm)
                )
            else:
                raise CertificateError("Unsupported public key type.")
            return True
        except InvalidSignature:
            raise CertificateError("Invalid X.509 Certificate: Untrusted Root CA (signature verification failed).")
        except CertificateError:
            raise
        except Exception as e:
            raise CertificateError(f"Invalid X.509 Certificate: {e}")
        
    @staticmethod
    def ecdh_key_exchange(private_key_a: bytes, public_key_b: bytes) -> bytes:
        """Elliptic Curve Diffie-Hellman key agreement using X25519 and HKDF."""
        from cryptography.hazmat.primitives.asymmetric import x25519
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
        try:
            priv = load_pem_private_key(private_key_a, password=None)
            pub = load_pem_public_key(public_key_b)
            
            if not isinstance(priv, x25519.X25519PrivateKey) or not isinstance(pub, x25519.X25519PublicKey):
                raise ProtocolError("ECDH Key Exchange failed: Keys must be X25519")
                
            shared_secret = priv.exchange(pub)
            
            derived_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'vireon-fixed-salt-or-exchange',
                info=b'vireon handshake data',
            ).derive(shared_secret)
            return derived_key
        except Exception as e:
            raise ProtocolError(f"ECDH Key Exchange failed: {e}")
        
    @staticmethod
    def aes_gcm_encrypt(key: bytes, iv: bytes, plaintext: bytes, aad: bytes) -> Tuple[bytes, bytes]:
        """Implements AES-GCM encryption with Auth Tag."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(key)
        ct_tag = aesgcm.encrypt(iv, plaintext, aad)
        return ct_tag[:-16], ct_tag[-16:]
        
    @staticmethod
    def aes_gcm_decrypt(key: bytes, iv: bytes, ciphertext: bytes, aad: bytes, tag: bytes) -> bytes:
        """Implements AES-GCM decryption and tag verification."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.exceptions import InvalidTag
        aesgcm = AESGCM(key)
        try:
            return aesgcm.decrypt(iv, ciphertext + tag, aad)
        except InvalidTag:
            raise ProtocolError("AES-GCM Auth Tag verification failed (malicious modification)")

class RFFrameProcessor:
    """
    Simulates packet-level RF/BLE telemetry frame processing.
    
    Frame format:
    [Preamble (1B) | Length (1B) | SeqNo (2B) | PayloadType (1B) | Payload (NB) | Checksum/HMAC (2B/32B)]
    Preamble: 0xAA
    """
    PREAMBLE = 0xAA
    HEADER_STRUCT = struct.Struct(">BBHB")  # Preamble, Length, SeqNo, PayloadType
    
    def __init__(self, shared_key: bytes):
        if not shared_key or len(shared_key) != 32:
            raise ValueError("RFFrameProcessor requires a securely derived 32-byte shared_key")
        self.SHARED_KEY = shared_key
        self.expected_seq_no = 0
        self.consecutive_failures: dict[str, int] = {}
        self.sleep_until: dict[str, float] = {}
        self.sleep_duration: dict[str, float] = {}
        self.session_key = self.SHARED_KEY
        self.iv_counter = 0

    def derive_session_key(self, salt: bytes):
        """Derive ephemeral session key using shared key and salt."""
        self.session_key = hmac.new(self.SHARED_KEY, salt, hashlib.sha256).digest()

    def calculate_crc16(self, data: bytes) -> int:
        """Standard CRC-16-CCITT checksum."""
        crc = 0xFFFF
        for byte in data:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc

    def calculate_hmac(self, data: bytes) -> bytes:
        """HMAC-SHA256 signature for cryptographic frame integrity."""
        return hmac.new(self.session_key, data, hashlib.sha256).digest()

    def pack_frame(self, seq_no: int, payload_type: int, payload: bytes, secure_mode: bool = False) -> bytes:
        """Pack payload into a binary telemetry frame."""
        # Header without length initially
        if secure_mode:
            # Emulate AES-GCM: IV (12B) + Ciphertext + Tag (16B)
            total_len = 5 + 12 + len(payload) + 16
            header = struct.pack(">BBHB", self.PREAMBLE, total_len, seq_no, payload_type)
            iv = struct.pack(">Q", self.iv_counter) + b"\x00\x00\x00\x00" # AES-GCM needs 12-byte IV
            self.iv_counter += 1
            ciphertext, tag = CryptoEmulator.aes_gcm_encrypt(self.session_key, iv, payload, aad=header)
            return header + iv + ciphertext + tag
        else:
            total_len = 5 + len(payload) + 2
            header = struct.pack(">BBHB", self.PREAMBLE, total_len, seq_no, payload_type)
            frame_body = header + payload
            crc = self.calculate_crc16(frame_body)
            return frame_body + struct.pack(">H", crc)

    def unpack_frame(self, frame_bytes: bytes, secure_mode: bool = False, current_time: float = 0.0, source_id: str = "default") -> Tuple[int, int, bytes]:
        """
        Unpack and validate a binary telemetry frame with flood-protection duty cycling.
        
        Returns:
            Tuple[seq_no, payload_type, payload]
        Raises:
            ProtocolError if frame is malformed, out of sequence, corrupted, or if receiver is asleep.
        """
        sleep_until = self.sleep_until.get(source_id, 0.0)
        if current_time < sleep_until:
            raise ProtocolError(f"RF Receiver is sleeping for source {source_id} due to telemetry flooding protection. Sleep remaining: {sleep_until - current_time:.1f}s")

        try:
            if len(frame_bytes) < 7:
                raise ProtocolError("Frame too short")
                
            preamble, length, seq_no, payload_type = self.HEADER_STRUCT.unpack(frame_bytes[:5])
            
            if preamble != self.PREAMBLE:
                raise ProtocolError(f"Invalid preamble: 0x{preamble:02X}")
                
            if len(frame_bytes) != length:
                raise ProtocolError(f"Frame length mismatch: expected {length}, got {len(frame_bytes)}")
                
            # Verify integrity
            if secure_mode:
                if len(frame_bytes) < 5 + 12 + 16:
                    raise ProtocolError("Secure frame too short")
                header = frame_bytes[:5]
                iv = frame_bytes[5:17]
                tag = frame_bytes[-16:]
                ciphertext = frame_bytes[17:-16]
                payload = CryptoEmulator.aes_gcm_decrypt(self.session_key, iv, ciphertext, aad=header, tag=tag)
            else:
                payload_end = length - 2
                payload = frame_bytes[5:payload_end]
                received_crc_bytes = frame_bytes[payload_end:]
                received_crc = struct.unpack(">H", received_crc_bytes)[0]
                calculated_crc = self.calculate_crc16(frame_bytes[:payload_end])
                if received_crc != calculated_crc:
                    raise ProtocolError(f"CRC-16 mismatch: received 0x{received_crc:04X}, calculated 0x{calculated_crc:04X}")

            # Verify sequence number (prevent replay attacks & sequence lockout DoS)
            if seq_no < self.expected_seq_no:
                raise ProtocolError(f"Replay attack detected: SeqNo {seq_no} < expected {self.expected_seq_no}")
            if seq_no > self.expected_seq_no + 100:
                raise ProtocolError(f"Sequence out of window: SeqNo {seq_no} > expected {self.expected_seq_no} + 100 (lockout prevention)")
                    
            # Success: reset counters
            self.expected_seq_no = seq_no + 1
            self.consecutive_failures[source_id] = 0
            self.sleep_until[source_id] = 0.0
            self.sleep_duration[source_id] = 5.0
            return seq_no, payload_type, payload
            
        except ProtocolError as e:
            failures = self.consecutive_failures.get(source_id, 0) + 1
            self.consecutive_failures[source_id] = failures
            duration = self.sleep_duration.get(source_id, 5.0)
            if failures >= 3:
                self.sleep_until[source_id] = current_time + duration
                self.sleep_duration[source_id] = min(60.0, duration * 2.0)
            raise e
