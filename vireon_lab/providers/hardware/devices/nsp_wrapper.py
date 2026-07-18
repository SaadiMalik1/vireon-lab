# Copyright 2026 VIREON Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import os
import hashlib
import json
from typing import Any, List
from vireon_lab.providers.hardware.devices import IDeviceWrapper

class NSPCryptographicWrapper(IDeviceWrapper):
    """
    Simulates the Neural Sensory Protocol (NSP) advanced cryptographic wrapper.
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
        # Simulate computational overhead of advanced cryptography on low-power chips
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

    def get_board(self) -> Any:
        return None

    def get_eeg_channels(self) -> List[int]:
        return []

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def read_chunk(self, start_sample: int, num_samples: int) -> Any:
        return None

    def send_eeg_data(self, data: Any) -> None:
        pass
