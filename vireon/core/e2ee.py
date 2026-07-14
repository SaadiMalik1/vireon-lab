"""
End-to-End Encryption (E2EE) Layer for Neural Data.

Simulates an E2EE channel between the firmware/hardware layer and the final
clinical endpoint (e.g., cloud backend or secure display), bypassing intermediate
vulnerable nodes like mobile phones or PC relays.
Uses simulated Hybrid Crypto (ECDH for key exchange + AES-GCM for payload).
"""

import os
import json
import base64
import time
from typing import Dict, Any, Optional

class E2EEChannel:
    def __init__(self, key_rotation_interval_sec: float = 3600.0):
        self.key_rotation_interval_sec = key_rotation_interval_sec
        self.session_key: Optional[bytes] = None
        self.key_established_time = 0.0
        self.packets_since_rotation = 0

    def establish_session(self) -> bool:
        """Simulates ECDH key exchange to establish a shared AES-GCM session key."""
        print("[E2EEChannel] Establishing ECDH session key...")
        self.session_key = os.urandom(32)
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
            print("[E2EEChannel] Rotating AES-GCM session key...")
            self.session_key = os.urandom(32)
            self.key_established_time = time.time()
            self.packets_since_rotation = 0

    def encrypt_payload(self, data: Dict[str, Any]) -> str:
        """
        Simulates AES-GCM authenticated encryption.
        Returns a base64 encoded 'ciphertext' payload with a prepended IV and Appended MAC.
        """
        if not self.session_key:
            self.establish_session()
            
        self._rotate_key_if_needed()
        self.packets_since_rotation += 1
        
        # Serialize data
        plaintext = json.dumps(data).encode('utf-8')
        
        # Simulate AES-GCM structure: [IV (12 bytes)] + [Ciphertext] + [Auth Tag (16 bytes)]
        # Since this is a simulation, we just XOR with the key (repeating) and append mock structures.
        iv = os.urandom(12)
        auth_tag = os.urandom(16)
        
        # Simple XOR mock for ciphertext
        ciphertext = bytearray()
        for i, b in enumerate(plaintext):
            ciphertext.append(b ^ self.session_key[i % 32])
            
        final_payload = iv + bytes(ciphertext) + auth_tag
        return base64.b64encode(final_payload).decode('utf-8')

    def decrypt_payload(self, encrypted_b64: str) -> Dict[str, Any]:
        """
        Simulates AES-GCM decryption and authentication.
        """
        if not self.session_key:
            raise ValueError("No session key established")
            
        raw = base64.b64decode(encrypted_b64)
        if len(raw) < 28:
            raise ValueError("Invalid AES-GCM payload size")
            
        ciphertext = raw[12:-16]
        
        # Simple XOR mock decryption
        plaintext = bytearray()
        for i, b in enumerate(ciphertext):
            plaintext.append(b ^ self.session_key[i % 32])
            
        return json.loads(bytes(plaintext).decode('utf-8'))
