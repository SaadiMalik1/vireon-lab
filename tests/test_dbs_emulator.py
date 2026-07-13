import unittest
import numpy as np
from vireon.core.twin import DigitalTwin
from vireon.plugins.clinical.dbs_emulator import LFPGenerator, ClosedLoopDBSController

class TestDBSClosedLoop(unittest.TestCase):
    def setUp(self):
        self.twin = DigitalTwin(num_channels=8)
        self.generator = LFPGenerator(sample_rate=250, num_channels=8)
        self.controller = ClosedLoopDBSController(self.twin)

    def test_lfp_generator_states(self):
        # 1. Nominal state check
        chunk_none = self.generator.read_chunk(100, "none")
        self.assertEqual(chunk_none.shape, (8, 100))
        initial_amplitude = self.generator.base_beta_amplitude
        
        # 2. Suppress state check (amplitude should drop)
        self.generator.read_chunk(250, "suppress")
        self.assertLess(self.generator.base_beta_amplitude, initial_amplitude)
        
        # 3. Sync state check (amplitude should rise)
        suppressed_amp = self.generator.base_beta_amplitude
        self.generator.read_chunk(250, "sync")
        self.assertGreater(self.generator.base_beta_amplitude, suppressed_amp)

    def test_controller_therapeutic_suppression(self):
        # Generate raw Parkinsonian data (high beta oscillation)
        data = self.generator.read_chunk(250, "none")
        
        # Feed LFP to controller (attack=False)
        self.controller.process_lfp(data, [0, 1], 250, attack_active=False)
        
        # Biomarker threshold exceeded => stimulation should activate out-of-phase (suppress)
        self.assertTrue(self.twin.get_state()["stimulation_enabled"])
        self.assertEqual(self.controller.stimulation_mode, "suppress")
        self.assertFalse(self.twin.get_state()["clinical_alert_active"])
        self.assertEqual(self.twin.get_state()["decoder_confidence"], 0.95)

    def test_controller_pathological_synchronization(self):
        # Generate raw Parkinsonian data (high beta oscillation)
        data = self.generator.read_chunk(250, "none")
        
        # Feed LFP to controller under phase-shifting attack (attack=True)
        self.controller.process_lfp(data, [0, 1], 250, attack_active=True)
        
        # Synchronization should activate and trigger pathological alert
        self.assertTrue(self.twin.get_state()["stimulation_enabled"])
        self.assertEqual(self.controller.stimulation_mode, "sync")
        self.assertTrue(self.twin.get_state()["clinical_alert_active"])
        self.assertEqual(self.twin.get_state()["clinical_status"], "Pathological Sync Alert")
        self.assertEqual(self.twin.get_state()["decoder_confidence"], 0.0)

if __name__ == "__main__":
    unittest.main()
