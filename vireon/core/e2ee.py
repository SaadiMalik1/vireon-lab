"""
End-to-End Encryption (E2EE) Layer for Neural Data.

Simulates an E2EE channel between the firmware/hardware layer and the final
clinical endpoint (e.g., cloud backend or secure display), bypassing intermediate
vulnerable nodes like mobile phones or PC relays.
Uses simulated Hybrid Crypto (ECDH for key exchange + AES-GCM for payload).

WARNING: This module provides a simulation of E2EE. Although it uses AES-GCM, 
key exchange and storage are simulated for the digital twin environment. 
Do not use this implementation for production or real human use.
"""

import os
import json
import base64
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class E2EEChannel:
    def __init__(self, key_rotation_interval_sec: float = 3600.0):
        self.key_rotation_interval_sec = key_rotation_interval_sec
        self.session_key: Optional[bytes] = None
        self.key_established_time = 0.0
        self.packets_since_rotation = 0

    def establish_session(self) -> bool:
        """Simulates ECDH key exchange to establish a shared AES-GCM session key."""
        logger.info("[E2EEChannel] Establishing ECDH session key...")
        from cryptography.hazmat.primitives.asymmetric import x25519
        from cryptography.hazmat.primitives import serialization
        from vireon.core.protocol import CryptoEmulator
        
        client_priv = x25519.X25519PrivateKey.generate()
        client_priv_bytes = client_priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        server_priv = x25519.X25519PrivateKey.generate()
        server_pub = server_priv.public_key()
        server_pub_bytes = server_pub.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        self.session_key = CryptoEmulator.ecdh_key_exchange(client_priv_bytes, server_pub_bytes)
        self.key_established_time = time.time()
        self.packets_since_rotation = 0
        return True

    def _rotate_key_if_needed(self):
        """Rotates the key based on time or packet limits (e.g., AES-GCM tag collision limits)."""
        if not self.session_key:
            return
            
        time_elapsed = time.time() - self.key_established_time
        # NIST SP 800-38D recommends rotating AES-GCM keys before 2^32 invocations
        # We simulate a rotation bound based on interval or packet count
        if time_elapsed > self.key_rotation_interval_sec or self.packets_since_rotation > 100000:
            logger.info("[E2EEChannel] Rotating AES-GCM session key...")
            self.establish_session()

    def encrypt_payload(self, data: Dict[str, Any]) -> str:
        """
        AES-GCM authenticated encryption.
        Returns a base64 encoded 'ciphertext' payload with a prepended IV and Appended MAC.
        """
        if not self.session_key:
            self.establish_session()
            
        self._rotate_key_if_needed()
        self.packets_since_rotation += 1
        
        # Serialize data
        plaintext = json.dumps(data).encode('utf-8')
        
        iv = os.urandom(12)
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(self.session_key)
        ciphertext = aesgcm.encrypt(iv, plaintext, b'vireon-e2ee-context')
        
        # AESGCM.encrypt returns ciphertext with the tag appended
        final_payload = iv + ciphertext
        return base64.b64encode(final_payload).decode('utf-8')

    def decrypt_payload(self, encrypted_b64: str) -> Dict[str, Any]:
        """
        AES-GCM decryption and authentication.
        """
        if not self.session_key:
            raise ValueError("No session key established")
            
        raw = base64.b64decode(encrypted_b64)
        if len(raw) < 28:
            raise ValueError("Invalid AES-GCM payload size")
            
        iv = raw[:12]
        ciphertext = raw[12:]
        
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(self.session_key)
        try:
            plaintext = aesgcm.decrypt(iv, ciphertext, b'vireon-e2ee-context')
        except Exception as e:
            raise ValueError("AES-GCM Auth Tag verification failed") from e
            
        return json.loads(plaintext.decode('utf-8'))
