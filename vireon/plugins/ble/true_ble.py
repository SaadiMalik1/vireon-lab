from typing import Optional, Callable
from bleak import BleakClient, BleakScanner
from vireon.plugins.devices.hardware_bridge import HardwareBridge

class TrueBLEClient:
    """
    Connects to physical BLE wearables using bleak.
    Can feed real characteristic data into the HardwareBridge or DigitalTwin.
    """
    def __init__(self, mac_address: str, bridge: Optional[HardwareBridge] = None):
        self.mac_address = mac_address
        self.bridge = bridge
        self.client: Optional[BleakClient] = None
        self._connected = False
        self._notify_callbacks: dict[str, Callable] = {}

    async def connect(self) -> bool:
        """Discover and connect to the physical BLE device."""
        print(f"[TrueBLEClient] Scanning for {self.mac_address}...")
        device = await BleakScanner.find_device_by_address(self.mac_address, timeout=10.0)
        if not device:
            print(f"[TrueBLEClient] Device {self.mac_address} not found.")
            return False

        print(f"[TrueBLEClient] Found {device.name}. Connecting...")
        self.client = BleakClient(device)
        try:
            await self.client.connect()
            self._connected = True
            print(f"[TrueBLEClient] Connected to {self.mac_address}.")
            return True
        except Exception as e:
            print(f"[TrueBLEClient] Connection failed: {e}")
            return False

    async def disconnect(self):
        if self.client and self.client.is_connected:
            await self.client.disconnect()
        self._connected = False
        print(f"[TrueBLEClient] Disconnected from {self.mac_address}.")

    @property
    def is_connected(self) -> bool:
        return self.client.is_connected if self.client else False

    async def read_characteristic(self, char_uuid: str) -> Optional[bytes]:
        if not self.is_connected:
            raise ConnectionError("Not connected to BLE device.")
        data = await self.client.read_gatt_char(char_uuid)
        return bytes(data)

    async def write_characteristic(self, char_uuid: str, data: bytes, response: bool = False):
        if not self.is_connected:
            raise ConnectionError("Not connected to BLE device.")
        await self.client.write_gatt_char(char_uuid, data, response=response)

    async def start_notify(self, char_uuid: str, callback: Callable[[int, bytearray], None]):
        if not self.is_connected:
            raise ConnectionError("Not connected to BLE device.")
        
        # We optionally wrap the callback to route data to the hardware bridge if needed
        async def _notify_handler(sender, data):
            if self.bridge:
                # If we have a loopback hardware bridge, we could push data to its client socket directly,
                # but typically HardwareBridge expects TCP stream. Here we might adapt it or just log it.
                pass
            callback(sender, data)
            
        await self.client.start_notify(char_uuid, _notify_handler)
        self._notify_callbacks[char_uuid] = _notify_handler

    async def stop_notify(self, char_uuid: str):
        if not self.is_connected:
            return
        if char_uuid in self._notify_callbacks:
            await self.client.stop_notify(char_uuid)
            del self._notify_callbacks[char_uuid]
