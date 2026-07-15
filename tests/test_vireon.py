import unittest
import numpy as np
import time
from vireon.core.twin import DigitalTwin
from vireon.core.attack import (
    SignalAttackEngine,
    NoiseInjectionAttack,
    SignalDriftAttack,
    ImpedanceSpikeAttack,
    SignalSuppressionAttack
)
from vireon.core.engine import ReplayEngine
from vireon.core.utils import calculate_rms

class TestDigitalTwin(unittest.TestCase):
    def setUp(self):
        self.twin = DigitalTwin(device_id="test_board", sample_rate=250, num_channels=8)

    def test_initialization(self):
        state = self.twin.get_state()
        self.assertEqual(state["device_id"], "test_board")
        self.assertTrue(state["connected"])
        self.assertEqual(state["battery_level"], 100.0)
        self.assertEqual(state["decoder_confidence"], 1.0)
        self.assertFalse(state["clinical_alert_active"])
        self.assertEqual(state["clinical_status"], "Nominal")

    def test_impedance_updates(self):
        self.twin.update_impedance(0, 12.5)
        state = self.twin.get_state()
        self.assertEqual(state["electrode_impedances"]["0"], 12.5)
        # Verify invalid channel is ignored
        self.twin.update_impedance(99, 50.0)
        self.assertNotIn("99", state["electrode_impedances"])

    def test_decoder_confidence_limits(self):
        self.twin.update_decoder_confidence(1.5)
        self.assertEqual(self.twin.get_state()["decoder_confidence"], 1.0)
        self.twin.update_decoder_confidence(-0.5)
        self.assertEqual(self.twin.get_state()["decoder_confidence"], 0.0)

    def test_history_logging(self):
        initial_history_len = len(self.twin.get_history())
        self.twin.set_connection(False)
        self.assertEqual(len(self.twin.get_history()), initial_history_len + 1)
        self.assertEqual(self.twin.get_history()[-1]["connected"], False)

    def test_snapshot_and_restore(self):
        # Set some non-default states
        self.twin.hazard_state = "WARNING"
        self.twin.fallback_mode_enabled = True
        self.twin.neural_dynamics.beta_power = 0.75
        self.twin.neural_dynamics.coherence = 0.8
        
        snap = self.twin.snapshot()
        
        # Reset and restore
        self.twin = DigitalTwin(device_id="test_board")
        self.assertEqual(self.twin.hazard_state, "NOMINAL")
        
        self.twin.restore(snap)
        
        self.assertEqual(self.twin.hazard_state, "WARNING")
        self.assertTrue(self.twin.fallback_mode_enabled)
        self.assertEqual(self.twin.neural_dynamics.beta_power, 0.75)
        self.assertEqual(self.twin.neural_dynamics.coherence, 0.8)

class TestSignalModifiers(unittest.TestCase):
    def setUp(self):
        self.twin = DigitalTwin(num_channels=8)
        self.eeg_channels = [0, 1, 2, 3, 4, 5, 6, 7]
        self.sample_rate = 250
        # Generate 1 second of flat data (zeros)
        self.data = np.zeros((8, 250))

    def test_noise_injection(self):
        noise_attack = NoiseInjectionAttack(target_channels=[0, 2], noise_level_microvolts=10.0)
        mutated = noise_attack.apply(self.data, self.eeg_channels, self.sample_rate, self.twin)
        
        # Verify shape
        self.assertEqual(mutated.shape, self.data.shape)
        # Targeted channels should have signal variance > 0
        self.assertGreater(np.var(mutated[0, :]), 0.0)
        self.assertGreater(np.var(mutated[2, :]), 0.0)
        # Untargeted channels should remain clean/flat
        self.assertEqual(np.var(mutated[1, :]), 0.0)

    def test_signal_drift(self):
        drift_attack = SignalDriftAttack(target_channels=[1], drift_rate_uv_per_sec=100.0)
        # First chunk
        mutated1 = drift_attack.apply(self.data, self.eeg_channels, self.sample_rate, self.twin)
        # Second chunk
        mutated2 = drift_attack.apply(self.data, self.eeg_channels, self.sample_rate, self.twin)
        
        # Last sample of chunk 1 should be less than last sample of chunk 2 due to drift accumulation
        self.assertGreater(mutated2[1, -1], mutated1[1, -1])

    def test_impedance_spike(self):
        spike_attack = ImpedanceSpikeAttack(target_channels=[3], spike_value_kohm=200.0)
        mutated = spike_attack.apply(self.data, self.eeg_channels, self.sample_rate, self.twin)
        
        # Check that digital twin impedance was modified
        self.assertEqual(self.twin.electrode_impedances[3], 200.0)
        # Check noise injection
        self.assertGreater(calculate_rms(mutated[3, :]), 10.0)

    def test_signal_suppression(self):
        ones_data = np.ones((8, 250)) * 100.0
        suppression_attack = SignalSuppressionAttack(target_channels=[4], attenuation_factor=0.01)
        mutated = suppression_attack.apply(ones_data, self.eeg_channels, self.sample_rate, self.twin)
        
        # Channel 4 should be attenuated
        self.assertAlmostEqual(mutated[4, 0], 1.0)
        # Channel 0 should remain unchanged
        self.assertEqual(mutated[0, 0], 100.0)

class TestReplayEngine(unittest.TestCase):
    def setUp(self):
        self.twin = DigitalTwin(num_channels=8)
        self.attack_engine = SignalAttackEngine(self.twin)
        self.engine = ReplayEngine(self.twin, self.attack_engine)

    def test_start_stop(self):
        self.assertFalse(self.engine.running)
        self.engine.start(interval_sec=0.05)
        self.assertTrue(self.engine.running)
        time.sleep(0.1)
        self.engine.stop()
        self.assertFalse(self.engine.running)

if __name__ == "__main__":
    unittest.main()
