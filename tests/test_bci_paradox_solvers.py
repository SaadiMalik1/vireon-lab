import unittest
import numpy as np
from vireon.core.twin import DigitalTwin
from vireon.core.security import NeuroSignalAssuranceEngine, NeuroIPS
from vireon.core.protocol import RFFrameProcessor, ProtocolError

class TestBCIParadoxSolvers(unittest.TestCase):
    def setUp(self):
        self.twin = DigitalTwin(num_channels=8)
        self.twin.fallback_mode_enabled = True
        self.ids = NeuroSignalAssuranceEngine(self.twin)
        self.ips = NeuroIPS(self.twin, self.ids)

    def test_active_impedance_probe(self):
        # 1. Nominal LFP signal (normal variance)
        nominal_data = np.random.normal(0, 10.0, (8, 250))
        res = self.twin.verify_electrode_impedances(nominal_data)
        self.assertTrue(res)
        self.assertEqual(self.twin.electrode_impedances[0], 5.0)

        # 2. High-noise spoofing signal
        noise_data = np.random.normal(0, 500.0, (8, 250))
        res = self.twin.verify_electrode_impedances(noise_data)
        self.assertFalse(res)
        self.assertEqual(self.twin.electrode_impedances[0], 60.0)

        # 3. Suppressed / flatline signal
        flat_data = np.zeros((8, 250))
        res = self.twin.verify_electrode_impedances(flat_data)
        self.assertFalse(res)
        self.assertEqual(self.twin.electrode_impedances[0], 100.0)

    def test_safe_fallback_therapy(self):
        # Activate safe fallback
        self.twin.enable_fallback_mode(True)
        self.assertTrue(self.twin.fallback_mode_active)
        self.assertTrue(self.twin.stimulation_enabled)
        self.assertEqual(self.twin.stimulation_amplitude_ma, 1.5)
        self.assertEqual(self.twin.stimulation_frequency_hz, 130.0)

        # Attempts to update or shut off therapy are blocked during fallback
        self.twin.update_therapy(False)
        self.assertTrue(self.twin.stimulation_enabled)

        self.twin.update_stimulation_params(4.0, 150.0)
        self.assertEqual(self.twin.stimulation_amplitude_ma, 1.5)
        self.assertEqual(self.twin.stimulation_frequency_hz, 130.0)

        # Pathological synchronization attack triggers fallback mode
        self.twin.enable_fallback_mode(False)  # Reset
        self.ips.mitigate_pathological_sync(["PATHOLOGICAL_SYNCHRONIZATION_ATTACK"])
        self.assertTrue(self.twin.fallback_mode_active)
        self.assertEqual(self.twin.clinical_status, "Degraded (Safe Fallback)")

    def test_patient_state_coherence_model(self):
        # Establish stable starting settings in history
        self.ips.stim_history = [(0.0, 1.0, 130.0)]
        self.ids.history_beta_power = [25.0]

        # 1. Delta rate limit check: Jump from 1.0 to 3.0 mA is clamped to 1.5 mA (1.0 + 0.5)
        amp, freq = self.ips.sanitize_stimulation_write(3.0, 130.0)
        self.assertEqual(amp, 1.5)
        self.assertTrue(self.ips.clamping_active)

        # 2. State coherence: Beta power is low (10.0 uV^2), trying to increase stim amplitude should be blocked
        self.ids.history_beta_power = [10.0]
        # Re-establish stable setting as 1.5 mA
        self.ips.stim_history = [(1.0, 1.5, 130.0)]
        
        amp, freq = self.ips.sanitize_stimulation_write(2.0, 130.0)  # delta is 0.5 (under delta limit)
        self.assertEqual(amp, 1.5)  # Blocked and kept at last amplitude (1.5) because beta power is low
        self.assertTrue(self.ips.clamping_active)

    def test_telemetry_sleep_duty_cycling(self):
        processor = RFFrameProcessor()
        
        # Perform 3 consecutive unpacking failures
        for _ in range(3):
            with self.assertRaises(ProtocolError):
                # Unpack short/invalid frame
                processor.unpack_frame(b"\x00\x00\x00", secure_mode=False, current_time=1.0)

        # The receiver is now asleep (sleep_until = 1.0 + 5.0 = 6.0)
        self.assertEqual(processor.consecutive_failures, 3)
        self.assertEqual(processor.sleep_until, 6.0)

        # Subsequent valid frame throws error due to sleep status
        valid_frame = processor.pack_frame(0, 0x01, b"test", secure_mode=False)
        with self.assertRaises(ProtocolError) as context:
            processor.unpack_frame(valid_frame, secure_mode=False, current_time=4.0)
        self.assertIn("sleeping", str(context.exception))

        # Once time advances past sleep_until, frames are accepted and reset sleep state
        seq, ptype, unpacked = processor.unpack_frame(valid_frame, secure_mode=False, current_time=7.0)
        self.assertEqual(unpacked, b"test")
        self.assertEqual(processor.consecutive_failures, 0)
        self.assertEqual(processor.sleep_until, 0.0)

if __name__ == "__main__":
    unittest.main()
