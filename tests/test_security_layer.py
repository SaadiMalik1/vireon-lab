import unittest
import numpy as np
from vireon.core.twin import DigitalTwin
from vireon.core.security import NeuroSignalAssuranceEngine, NeuroIPS, BLELinkGuard

class TestNeuroSecurityLayer(unittest.TestCase):
    def setUp(self):
        self.twin = DigitalTwin(num_channels=8)
        self.ids = NeuroSignalAssuranceEngine(self.twin)
        self.ips = NeuroIPS(self.twin, self.ids)
        self.link_guard = BLELinkGuard(self.twin)

    def test_ids_signal_anomalies(self):
        # 1. Test extreme noise detection
        noisy_data = np.ones((8, 100)) * 200.0
        anomalies = self.ids.analyze_signal(noisy_data)
        self.assertIn("HIGH_NOISE_ANOMALY", anomalies)

        # 2. Test signal suppression detection
        suppressed_data = np.zeros((8, 100))
        anomalies = self.ids.analyze_signal(suppressed_data)
        self.assertIn("SIGNAL_SUPPRESSION_ANOMALY", anomalies)

        # 3. Clean signal check
        # Instantiate fresh IDS to avoid stateful CUSUM/Autoencoder drift triggers
        ids_fresh = NeuroSignalAssuranceEngine(self.twin)
        clean_data = np.random.normal(0, 10.0, (8, 100))
        anomalies = ids_fresh.analyze_signal(clean_data)
        self.assertEqual(len(anomalies), 0)

    def test_ids_pathological_sync_detection(self):
        # Simulate beta power sequence remaining high during stimulation
        for _ in range(12):
            anomalies = self.ids.analyze_clinical(65.0, stim_enabled=True, amplitude=2.5)
            
        self.assertIn("PATHOLOGICAL_SYNCHRONIZATION_ATTACK", anomalies)

    def test_ips_command_clamping(self):
        # Unsafe command write (10.0 mA)
        amp, freq = self.ips.sanitize_stimulation_write(10.0, 130.0)
        
        # Should clamp to 4.0 mA maximum safety ceiling
        self.assertEqual(amp, 4.0)
        self.assertEqual(freq, 130.0)
        self.assertEqual(self.ips.blocked_attacks_count, 1)
        self.assertTrue(self.ips.clamping_active)
        
        # Verify twin state updated to warning/marginal
        state = self.twin.get_state()
        self.assertEqual(state["hazard_state"], "WARNING")
        self.assertEqual(state["iso_severity"], "MARGINAL")

    def test_ips_signal_mitigation(self):
        # Generate noisy array
        noisy_data = np.ones((8, 100)) * 200.0
        anomalies = self.ids.analyze_signal(noisy_data)
        
        # Mitigate
        clean_data = self.ips.mitigate_signal_anomalies(noisy_data, anomalies)
        
        # Noise should be replaced with baseline nominal values (e.g. mean RMS < 5.0)
        rms = float(np.sqrt(np.mean(np.square(clean_data[0, :]))))
        self.assertLess(rms, 10.0)
        self.assertEqual(self.ips.blocked_attacks_count, 1)

    def test_ips_pathological_sync_mitigation(self):
        # Flag sync anomaly
        anomalies = ["PATHOLOGICAL_SYNCHRONIZATION_ATTACK"]
        self.twin.update_therapy(True)
        self.twin.update_stimulation_params(3.0, 130.0)
        
        suspended = self.ips.mitigate_pathological_sync(anomalies)
        
        # Should suspend stimulation and update state
        self.assertTrue(suspended)
        state = self.twin.get_state()
        self.assertFalse(state["stimulation_enabled"])
        self.assertEqual(state["stimulation_amplitude_ma"], 0.0)
        self.assertEqual(state["hazard_state"], "THERAPY_SUSPENDED")
        self.assertEqual(state["iso_severity"], "MARGINAL")

    def test_ble_link_guard_mtu(self):
        # Abusive MTU negotiation (5 bytes)
        safe_mtu = self.link_guard.verify_mtu(5)
        
        # Should enforce BLE specification minimum of 23 bytes
        self.assertEqual(safe_mtu, 23)
        self.assertEqual(self.link_guard.blocked_mtu_abuses, 1)
        self.assertTrue(self.twin.get_state()["clinical_alert_active"])

if __name__ == "__main__":
    unittest.main()
