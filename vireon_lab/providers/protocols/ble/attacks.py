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

import random
from vireon_lab.providers.ble.emulator import VirtualBLELink, VirtualBLEClient
from vireon.core.twin import DigitalTwin

class PairingFailureAttack:
    def __init__(self, twin: DigitalTwin):
        self.twin = twin

    def apply(self, client: VirtualBLEClient, link: VirtualBLELink):
        # Force disconnect due to pairing failure/rejection
        link.paired = False
        client.disconnect()
        # Propagate to Digital Twin state
        self.twin.set_connection(False)
        self.twin.set_clinical_alert(True, "BLE Pairing Fail")

class GATTCorruptionAttack:
    def __init__(self, corruption_probability: float = 0.5):
        self.corruption_probability = corruption_probability

    def apply(self, payload: bytes) -> bytes:
        if random.random() > self.corruption_probability:
            return payload
            
        # Flip bits in payload to emulate packet corruption
        data = bytearray(payload)
        if len(data) > 0:
            data[0] = data[0] ^ 0xFF  # Guarantee at least one byte is flipped
        for i in range(1, len(data)):
            if random.random() < 0.1: # 10% chance of byte corruption
                data[i] = data[i] ^ 0xFF
        return bytes(data)

class MTUAbuseAttack:
    def __init__(self, twin: DigitalTwin, abnormal_mtu: int = 5):
        self.twin = twin
        self.abnormal_mtu = abnormal_mtu

    def apply(self, client: VirtualBLEClient, link: VirtualBLELink):
        # Override MTU negotiation to violate specification (BLE min is 23)
        # Setting a tiny MTU causes excessive fragmentation or buffer overflows.
        link.mtu = self.abnormal_mtu
        self.twin.set_clinical_alert(True, f"Abnormal MTU Alert: {self.abnormal_mtu} bytes")

class MalformedNotificationAttack:
    def __init__(self, packet_size: int = 24):
        self.packet_size = packet_size

    def apply(self) -> bytes:
        # Generate garbage bytes instead of structured EEG floats
        return bytes(bytearray(random.getrandbits(8) for _ in range(self.packet_size)))

class BLESpoofingAttack:
    """
    Simulates a BLE Spoofing Attack (BLESA) / MITM.
    The attacker clones the MAC address of a trusted device to inject malicious
    commands or intercept telemetry.
    """
    def __init__(self, twin: DigitalTwin, spoofed_mac: str = "XX:XX:XX:XX:XX:XX"):
        self.twin = twin
        self.spoofed_mac = spoofed_mac

    def apply(self, client: VirtualBLEClient, link: VirtualBLELink):
        """Forces the client's MAC to the spoofed MAC and bypasses standard pairing."""
        print(f"[BLESpoofingAttack] Spoofing MAC address: {self.spoofed_mac}")
        client.client_mac = self.spoofed_mac
        link.paired = False
        self.twin.set_clinical_alert(True, f"BLESA MITM Attempt from {self.spoofed_mac}")
