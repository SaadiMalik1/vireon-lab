from typing import List, Dict

class GATTCharacteristic:
    def __init__(self, uuid: str, value: bytes = b"", permissions: List[str] = None):
        self.uuid = uuid
        self.value = value
        self.permissions = permissions or ["read"]
        self.cccd_subscribed = False

    def read(self) -> bytes:
        if "read" not in self.permissions:
            raise PermissionError("Characteristic is not readable")
        return self.value

    def write(self, new_val: bytes):
        if "write" not in self.permissions:
            raise PermissionError("Characteristic is not writable")
        self.value = new_val

class GATTService:
    def __init__(self, uuid: str):
        self.uuid = uuid
        self.characteristics: Dict[str, GATTCharacteristic] = {}

    def add_characteristic(self, char: GATTCharacteristic):
        self.characteristics[char.uuid] = char

class VirtualBLEServer:
    def __init__(self):
        self.services: Dict[str, GATTService] = {}
        self._setup_services()

    def _setup_services(self):
        # 1. Device Info Service (0x180A)
        dev_info = GATTService("180A")
        dev_info.add_characteristic(GATTCharacteristic("2A29", b"VIREON Wearables"))  # Manufacturer
        dev_info.add_characteristic(GATTCharacteristic("2A26", b"1.0.0-ble"))            # Firmware
        self.services["180A"] = dev_info

        # 2. Biosignal Service (0xFE8D)
        biosignal = GATTService("FE8D")
        # EEG data notification characteristic (CCCD notify enabled)
        biosignal.add_characteristic(GATTCharacteristic("2D30", b"", ["read", "notify"]))
        # Control & Stimulation configuration characteristic
        biosignal.add_characteristic(GATTCharacteristic("2D31", b"\x00\x00", ["read", "write"]))
        self.services["FE8D"] = biosignal

    def get_characteristic(self, service_uuid: str, char_uuid: str) -> GATTCharacteristic:
        if service_uuid not in self.services:
            raise KeyError(f"Service {service_uuid} not found")
        service = self.services[service_uuid]
        if char_uuid not in service.characteristics:
            raise KeyError(f"Characteristic {char_uuid} not found")
        return service.characteristics[char_uuid]

class VirtualBLELink:
    def __init__(self, server: VirtualBLEServer):
        self.server = server
        self.connected = False
        self.paired = False
        self.mtu = 23  # BLE default MTU
        import secrets
        self.pairing_code = f"{secrets.randbelow(1000000):06d}"
        
    def set_pairing_code(self, pin: str):
        """Allow injection of known PIN for testing purposes."""
        self.pairing_code = pin
        self.latency_ms = 15.0  # Connection interval latency

class VirtualBLEClient:
    def __init__(self, link: VirtualBLELink, client_mac: str = "AA:BB:CC:DD:EE:FF"):
        self.link = link
        self.client_mac = client_mac
        self.notifications_enabled = False
        self.received_packets: List[bytes] = []

    def connect(self) -> bool:
        # If the server has a link guard and a bonding database, check for BLESA
        server = self.link.server
        if hasattr(server, 'link_guard') and server.link_guard:
            if not server.link_guard.verify_connection(self.client_mac, self.link.paired, getattr(server, 'bonding_db', {})):
                return False
        
        self.link.connected = True
        return True

    def disconnect(self):
        self.link.connected = False
        self.notifications_enabled = False

    def pair(self, passkey: str) -> bool:
        if not self.link.connected:
            raise ConnectionError("Not connected")
        if passkey == self.link.pairing_code:
            self.link.paired = True
            return True
        else:
            self.link.paired = False
            return False

    def negotiate_mtu(self, requested_mtu: int) -> int:
        if not self.link.connected:
            raise ConnectionError("Not connected")
        # BLE MTU negotiation picks the minimum of client requested and server limit (typically 247)
        self.link.mtu = max(23, min(requested_mtu, 247))
        return self.link.mtu

    def enable_notifications(self, service_uuid: str, char_uuid: str, enable: bool):
        if not self.link.connected:
            raise ConnectionError("Not connected")
        char = self.link.server.get_characteristic(service_uuid, char_uuid)
        if "notify" not in char.permissions:
            raise ValueError("Characteristic does not support notifications")
        char.cccd_subscribed = enable
        self.notifications_enabled = enable

    def receive_notification(self, payload: bytes):
        """
        Receives packet frames from the server, emulating fragmentation based on MTU constraints.
        """
        if not self.link.connected or not self.notifications_enabled:
            return
            
        # MTU payload limit is MTU - 3 bytes header overhead
        payload_limit = self.link.mtu - 3
        
        # Fragment payload
        for offset in range(0, len(payload), payload_limit):
            fragment = payload[offset : offset + payload_limit]
            self.received_packets.append(fragment)
