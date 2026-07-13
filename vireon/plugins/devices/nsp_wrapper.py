import time
import os
import hashlib
import json

class NSPCryptographicWrapper:
    """
    Simulates the Neural Sensory Protocol (NSP) post-quantum cryptographic wrapper.
    In a real implementation, this would apply ML-KEM/Kyber key encapsulation 
    and AES-256-GCM authentication. Here, we simulate the computational overhead
    and append realistic metadata tags.
    """
    def __init__(self, simulate_latency_ms: float = 1.0):
        self.simulate_latency_ms = simulate_latency_ms
        # Generate a dummy session key identifier
        self.session_key_id = hashlib.sha256(os.urandom(16)).hexdigest()[:16]

    def encrypt_payload(self, payload: dict) -> dict:
        """
        Takes a telemetry payload, simulates encryption overhead, and wraps it with NSP metadata.
        """
        # Simulate computational overhead of post-quantum cryptography on low-power chips
        if self.simulate_latency_ms > 0:
            time.sleep(self.simulate_latency_ms / 1000.0)

        # Generate a simulated AES-256-GCM authentication tag for the payload
        # Ensure we don't modify the original dict directly
        payload_str = json.dumps(payload, sort_keys=True).encode('utf-8')
        auth_tag = hashlib.sha256(payload_str + os.urandom(8)).hexdigest()[:32]

        nsp_wrapper = {
            "nsp_active": True,
            "session_id": self.session_key_id,
            "cipher": "ML-KEM-768/AES-256-GCM",
            "auth_tag": auth_tag,
            "overhead_ms": self.simulate_latency_ms,
            "payload": payload
        }
        
        return nsp_wrapper

    def decrypt_payload(self, nsp_payload: dict) -> dict:
        """
        Simulates decrypting the payload and verifying the auth tag.
        """
        if self.simulate_latency_ms > 0:
            time.sleep(self.simulate_latency_ms / 1000.0)
            
        if "payload" in nsp_payload and "auth_tag" in nsp_payload:
            return nsp_payload["payload"]
        return nsp_payload
