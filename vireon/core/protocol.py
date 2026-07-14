import hmac
import hashlib
from typing import Tuple, Optional, Dict, Any

class ProtocolError(Exception):
    """Raised when frame validation fails."""
    pass

class CertificateError(ProtocolError):
    """Raised when X.509 validation fails."""
    pass

class CryptoEmulator:
    """Emulates NIST/FIPS compliant cryptography (X.509, ECDH, AES-GCM)."""
    
    @staticmethod
    def validate_x509_cert(cert_data: dict) -> bool:
        """Emulates X.509 certificate chain validation."""
        required_fields = ["issuer", "subject", "valid_from", "valid_to", "public_key", "signature"]
        if not all(k in cert_data for k in required_fields):
            raise CertificateError("Invalid X.509 Certificate: Missing required fields.")
            
        import time
        current_time = time.time()
        if current_time < cert_data["valid_from"] or current_time > cert_data["valid_to"]:
            raise CertificateError("Invalid X.509 Certificate: Expired or not yet valid.")
            
        if cert_data["signature"] != "VALID_ROOT_CA_SIG":
            raise CertificateError("Invalid X.509 Certificate: Untrusted Root CA.")
            
        return True
        
    @staticmethod
    def ecdh_key_exchange(private_key_a: bytes, public_key_b: bytes) -> bytes:
        """Emulates Elliptic Curve Diffie-Hellman key agreement."""
        # Emulation: The shared secret is just a hash of both keys sorted to be commutative
        combined = b"".join(sorted([private_key_a, public_key_b]))
        return hashlib.sha256(combined).digest()
        
    @staticmethod
    def aes_gcm_encrypt(key: bytes, iv: bytes, plaintext: bytes, aad: bytes) -> Tuple[bytes, bytes]:
        """Emulates AES-GCM encryption with Auth Tag."""
        # Simple XOR cipher for emulation
        ciphertext = bytes([b ^ key[i % len(key)] for i, b in enumerate(plaintext)])
        # Tag is HMAC of ciphertext + aad + iv
        tag_data = ciphertext + aad + iv
        tag = hmac.new(key, tag_data, hashlib.sha256).digest()[:16] # 128-bit tag
        return ciphertext, tag
        
    @staticmethod
    def aes_gcm_decrypt(key: bytes, iv: bytes, ciphertext: bytes, aad: bytes, tag: bytes) -> bytes:
        """Emulates AES-GCM decryption and tag verification."""
        expected_tag_data = ciphertext + aad + iv
        expected_tag = hmac.new(key, expected_tag_data, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, expected_tag):
            raise ProtocolError("AES-GCM Auth Tag verification failed (malicious modification)")
        plaintext = bytes([b ^ key[i % len(key)] for i, b in enumerate(ciphertext)])
        return plaintext

class RFFrameProcessor:
    """
    Simulates packet-level RF/BLE telemetry frame processing.
    
    Frame format:
    [Preamble (1B) | Length (1B) | SeqNo (2B) | PayloadType (1B) | Payload (NB) | Checksum/HMAC (2B/32B)]
    Preamble: 0xAA
    """
    PREAMBLE = 0xAA
    HEADER_STRUCT = struct.Struct(">BBHB")  # Preamble, Length, SeqNo, PayloadType
    SHARED_KEY = b"neuroshield_telemetry_secure_key_2026"

    def __init__(self):
        self.expected_seq_no = 0
        self.consecutive_failures = 0
        self.sleep_until = 0.0
        self.sleep_duration = 5.0
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
        header_partial = struct.pack(">B", self.PREAMBLE)
        
        if secure_mode:
            # Emulate AES-GCM: IV (8B) + Ciphertext + Tag (16B)
            total_len = 5 + 8 + len(payload) + 16
            header = struct.pack(">BBHB", self.PREAMBLE, total_len, seq_no, payload_type)
            iv = struct.pack(">Q", self.iv_counter)
            self.iv_counter += 1
            ciphertext, tag = CryptoEmulator.aes_gcm_encrypt(self.session_key, iv, payload, aad=header)
            return header + iv + ciphertext + tag
        else:
            total_len = 5 + len(payload) + 2
            header = struct.pack(">BBHB", self.PREAMBLE, total_len, seq_no, payload_type)
            frame_body = header + payload
            crc = self.calculate_crc16(frame_body)
            return frame_body + struct.pack(">H", crc)

    def unpack_frame(self, frame_bytes: bytes, secure_mode: bool = False, current_time: float = 0.0) -> Tuple[int, int, bytes]:
        """
        Unpack and validate a binary telemetry frame with flood-protection duty cycling.
        
        Returns:
            Tuple[seq_no, payload_type, payload]
        Raises:
            ProtocolError if frame is malformed, out of sequence, corrupted, or if receiver is asleep.
        """
        if current_time < self.sleep_until:
            raise ProtocolError(f"RF Receiver is sleeping due to telemetry flooding protection. Sleep remaining: {self.sleep_until - current_time:.1f}s")

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
                if len(frame_bytes) < 5 + 8 + 16:
                    raise ProtocolError("Secure frame too short")
                header = frame_bytes[:5]
                iv = frame_bytes[5:13]
                tag = frame_bytes[-16:]
                ciphertext = frame_bytes[13:-16]
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
            self.consecutive_failures = 0
            self.sleep_until = 0.0
            self.sleep_duration = 5.0
            return seq_no, payload_type, payload
            
        except ProtocolError as e:
            self.consecutive_failures += 1
            if self.consecutive_failures >= 3:
                self.sleep_until = current_time + self.sleep_duration
                self.sleep_duration = min(60.0, self.sleep_duration * 2.0)
            raise e
