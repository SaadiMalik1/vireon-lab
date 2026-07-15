import unittest
from vireon.core.twin import DigitalTwin

class TestCyberPhysicalRealism(unittest.TestCase):
    def test_simulation_mode_warning(self):
        # Simulation mode: should only warn, not shut down
        twin = DigitalTwin(hardware_mode=False)
        twin.stimulation_enabled = True
        twin.stimulation_amplitude_ma = 5.0  # High amplitude
        twin.stimulation_frequency_hz = 130.0
        
        # Advance clock to heat up tissue
        twin.set_sim_clock(100.0)
        twin.physics_engine.tick(twin, 100.0)
        
        self.assertEqual(twin.tissue_damage_risk, "HIGH")
        self.assertTrue(twin.clinical_alert_active)
        self.assertTrue(twin.stimulation_enabled)  # Still enabled!
        self.assertTrue("Physics Violation" in twin.clinical_status)

    def test_hardware_mode_shutdown(self):
        # Hardware mode: should shut down to protect tissue
        twin = DigitalTwin(hardware_mode=True)
        twin.stimulation_enabled = True
        twin.stimulation_amplitude_ma = 5.0
        twin.stimulation_frequency_hz = 130.0
        
        # Advance clock to heat up tissue
        twin.set_sim_clock(100.0)
        twin.physics_engine.tick(twin, 100.0)
        
        self.assertEqual(twin.hazard_state, "HARDWARE_SHUTDOWN")
        self.assertTrue(twin.clinical_alert_active)
        self.assertFalse(twin.stimulation_enabled)  # Disabled!
        self.assertEqual(twin.stimulation_amplitude_ma, 0.0)
        self.assertTrue("Hardware Failsafe" in twin.clinical_status)

if __name__ == '__main__':
    unittest.main()
