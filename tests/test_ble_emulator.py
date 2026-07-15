import unittest
from vireon.core.twin import DigitalTwin
from vireon.plugins.ble.emulator import VirtualBLEServer, VirtualBLELink, VirtualBLEClient
from vireon.plugins.ble.attacks import (
    PairingFailureAttack,
    GATTCorruptionAttack,
    MTUAbuseAttack,
    MalformedNotificationAttack
)

class TestBLEGATTStack(unittest.TestCase):
    def setUp(self):
        self.server = VirtualBLEServer()
        self.link = VirtualBLELink(self.server)
        self.link.set_pairing_code("123456")
        self.client = VirtualBLEClient(self.link)

    def test_gatt_database_structure(self):
        # Verify Device Info Service
        mfg = self.server.get_characteristic("180A", "2A29")
        self.assertEqual(mfg.read(), b"VIREON Wearables")
        
        # Verify Biosignal Service
        eeg_char = self.server.get_characteristic("FE8D", "2D30")
        self.assertIn("notify", eeg_char.permissions)

    def test_connection_and_pairing(self):
        # Connect
        self.assertFalse(self.link.connected)
        self.client.connect()
        self.assertTrue(self.link.connected)
        
        # Unsuccessful pairing
        paired = self.client.pair("000000")
        self.assertFalse(paired)
        self.assertFalse(self.link.paired)
        
        # Successful pairing
        paired = self.client.pair("123456")
        self.assertTrue(paired)
        self.assertTrue(self.link.paired)

    def test_mtu_negotiation_and_fragmentation(self):
        self.client.connect()
        
        # Default MTU is 23
        self.assertEqual(self.link.mtu, 23)
        
        # Negotiate larger MTU
        new_mtu = self.client.negotiate_mtu(100)
        self.assertEqual(new_mtu, 100)
        self.assertEqual(self.link.mtu, 100)
        
        # Enable notifications on EEG channel
        self.client.enable_notifications("FE8D", "2D30", True)
        self.assertTrue(self.client.notifications_enabled)
        
        # Send a 200-byte telemetry frame
        payload = b"X" * 200
        self.client.receive_notification(payload)
        
        # With MTU = 100, payload limit is 100 - 3 = 97 bytes.
        # 200 bytes will be fragmented into: 97 + 97 + 6 = 3 fragments.
        self.assertEqual(len(self.client.received_packets), 3)
        self.assertEqual(self.client.received_packets[0], b"X" * 97)
        self.assertEqual(self.client.received_packets[1], b"X" * 97)
        self.assertEqual(self.client.received_packets[2], b"X" * 6)

class TestBLELayerAttacks(unittest.TestCase):
    def setUp(self):
        self.twin = DigitalTwin(num_channels=8)
        self.server = VirtualBLEServer()
        self.link = VirtualBLELink(self.server)
        self.link.set_pairing_code("123456")
        self.client = VirtualBLEClient(self.link)

    def test_pairing_failure_attack(self):
        self.client.connect()
        self.client.pair("123456")
        self.assertTrue(self.link.paired)
        
        attack = PairingFailureAttack(self.twin)
        attack.apply(self.client, self.link)
        
        # Verify link states are dropped and digital twin updated
        self.assertFalse(self.link.paired)
        self.assertFalse(self.link.connected)
        self.assertFalse(self.twin.get_state()["connected"])
        self.assertEqual(self.twin.get_state()["clinical_status"], "BLE Pairing Fail")

    def test_gatt_corruption_attack(self):
        attack = GATTCorruptionAttack(corruption_probability=1.0)
        payload = b"clean_signal_bytes"
        corrupted = attack.apply(payload)
        
        # Corrupted payload should be modified/non-equal to clean signal
        self.assertNotEqual(corrupted, payload)
        self.assertEqual(len(corrupted), len(payload))

    def test_mtu_abuse_attack(self):
        self.client.connect()
        attack = MTUAbuseAttack(self.twin, abnormal_mtu=5)
        attack.apply(self.client, self.link)
        
        # Verify specification violation
        self.assertEqual(self.link.mtu, 5)
        self.assertTrue(self.twin.get_state()["clinical_alert_active"])
        self.assertIn("Abnormal MTU Alert", self.twin.get_state()["clinical_status"])

    def test_malformed_notification_attack(self):
        attack = MalformedNotificationAttack(packet_size=16)
        payload = attack.apply()
        
        # Verify payload length
        self.assertEqual(len(payload), 16)
        self.assertIsInstance(payload, bytes)

if __name__ == "__main__":
    unittest.main()
