import unittest
import numpy as np
from vireon.core.twin import DigitalTwin
from vireon_lab.providers.clinical.closed_loop import ClosedLoopSimulator, UncontrolledStimulationAttack

class TestClinicalRiskModeling(unittest.TestCase):
    def setUp(self):
        self.twin = DigitalTwin(num_channels=8)
        self.simulator = ClosedLoopSimulator(self.twin)
        self.eeg_channels = [0, 1, 2, 3, 4, 5, 6, 7]

    def test_nominal_state(self):
        data = np.ones((8, 100)) * 10.0
        self.simulator.process_signal(data, self.eeg_channels, 250)
        
        summary = self.simulator.get_clinical_summary()
        self.assertEqual(summary["hazard_state"], "NOMINAL")
        self.assertEqual(summary["iso_severity"], "NEGLIGIBLE")
        self.assertEqual(summary["tissue_damage_risk"], "NONE")
        self.assertEqual(summary["clinical_action"], "MONITOR")

    def test_warning_state(self):
        # Degrade electrode 0 slightly (impedance = 30.0)
        self.twin.update_impedance(0, 30.0)
        data = np.ones((8, 100)) * 10.0
        
        self.simulator.process_signal(data, self.eeg_channels, 250)
        
        summary = self.simulator.get_clinical_summary()
        self.assertEqual(summary["hazard_state"], "WARNING")
        self.assertEqual(summary["iso_severity"], "MARGINAL")
        self.assertEqual(summary["clinical_action"], "MONITOR")

    def test_therapy_suspended_state(self):
        # Disconnect client
        self.twin.set_connection(False)
        data = np.ones((8, 100)) * 10.0
        
        self.simulator.process_signal(data, self.eeg_channels, 250)
        
        summary = self.simulator.get_clinical_summary()
        self.assertEqual(summary["hazard_state"], "THERAPY_SUSPENDED")
        self.assertEqual(summary["iso_severity"], "MARGINAL")
        self.assertEqual(summary["clinical_action"], "SUSPEND_THERAPY")

    def test_pathological_sync_state(self):
        # Simulate pathological synchronization status
        self.twin.set_clinical_alert(True, "Pathological Sync Alert")
        data = np.ones((8, 100)) * 10.0
        
        self.simulator.process_signal(data, self.eeg_channels, 250)
        
        summary = self.simulator.get_clinical_summary()
        self.assertEqual(summary["hazard_state"], "PATHOLOGICAL_SYNCHRONIZATION")
        self.assertEqual(summary["iso_severity"], "CRITICAL")
        self.assertEqual(summary["tissue_damage_risk"], "MEDIUM")
        self.assertEqual(summary["clinical_action"], "SYNC_ALERT")

    def test_uncontrolled_stimulation_attack(self):
        # Inject firmware stimulation leak attack
        attack = UncontrolledStimulationAttack(self.twin)
        attack.apply()
        
        data = np.ones((8, 100)) * 10.0
        self.simulator.process_signal(data, self.eeg_channels, 250)
        
        summary = self.simulator.get_clinical_summary()
        self.assertEqual(summary["hazard_state"], "UNCONTROLLED_STIMULATION")
        self.assertEqual(summary["iso_severity"], "CATASTROPHIC")
        self.assertEqual(summary["tissue_damage_risk"], "HIGH")
        self.assertEqual(summary["clinical_action"], "SHUTDOWN_HARDWARE")
        
        # Verify safety locks bypassed
        self.assertTrue(self.twin.get_state()["stimulation_enabled"])
        self.assertEqual(self.twin.get_state()["stimulation_amplitude_ma"], 10.0)

if __name__ == "__main__":
    unittest.main()
