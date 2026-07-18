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

import unittest
import numpy as np
from vireon.core.twin import DigitalTwin
from vireon.core.detection import SecurityEngine
from vireon_lab.reference_providers.clinical import NeuroIPS
from vireon.core.protocol import RFFrameProcessor, ProtocolError

class TestAdversarialMitigations(unittest.TestCase):
    def setUp(self):
        self.twin = DigitalTwin(num_channels=8)
        self.ids = SecurityEngine(self.twin)
        self.ips = NeuroIPS(self.twin, self.ids)

    def test_sequence_window_and_dynamic_keys(self):
        processor = RFFrameProcessor(b"X"*32)
        
        # 1. Out of window sequence number raises error
        payload = b"test_window"
        frame_lockout = processor.pack_frame(seq_no=150, payload_type=0x01, payload=payload, secure_mode=False)
        with self.assertRaises(ProtocolError) as context:
            processor.unpack_frame(frame_lockout, secure_mode=False, current_time=0.0)
        self.assertIn("out of window", str(context.exception))

        # 2. Ephemeral session key derivation
        processor.derive_session_key(b"test_salt_123")
        self.assertNotEqual(processor.session_key, processor.SHARED_KEY)

        # Pack with session key
        frame_secure = processor.pack_frame(seq_no=0, payload_type=0x01, payload=payload, secure_mode=True)
        
        # Unpack works with the matching session key
        seq, ptype, unpacked = processor.unpack_frame(frame_secure, secure_mode=True, current_time=0.0)
        self.assertEqual(unpacked, payload)

        # Re-initialize another processor with default key -> unpack fails
        default_processor = RFFrameProcessor(b"X"*32)
        with self.assertRaises(ProtocolError) as context:
            default_processor.unpack_frame(frame_secure, secure_mode=True, current_time=0.0)
        self.assertIn("verification failed", str(context.exception))

    def test_thermodynamic_tissue_heating(self):
        # Initial temp is nominal
        self.assertEqual(self.twin.temperature_celsius, 37.0)

        # Enable high stimulation load
        self.twin.update_therapy(True)
        self.twin.update_stimulation_params(4.0, 130.0)
        
        # Advance simulation clock by 20 seconds
        self.twin.set_sim_clock(20.0)
        self.twin.physics_engine.tick(self.twin, 20.0)
        self.assertGreater(self.twin.temperature_celsius, 38.0)

        # Advance simulation clock by 100 seconds to exceed 40.5 limit
        self.twin.set_sim_clock(120.0)
        self.twin.physics_engine.tick(self.twin, 100.0)
        self.assertGreater(self.twin.temperature_celsius, 40.5)

        # Sanitize stim write now clamps to shutdown
        amp, freq = self.ips.sanitize_stimulation_write(2.0, 130.0)
        self.assertEqual(amp, 1.0)
        self.assertEqual(freq, 130.0)
        self.assertEqual(self.twin.hazard_state, "ENVELOPE_BREACH")
        # clinical_status is updated differently by the safety envelope check, we just verify hazard_state

    def test_spectral_consistency_check(self):
        np.random.seed(42)
        # 1. Broadband normal signal (high entropy)
        broadband_signal = np.random.normal(0, 15.0, (8, 250))
        anomalies = self.ids.analyze_signal(broadband_signal)
        self.assertNotIn("SPECTRAL_SPOOFING_ANOMALY", anomalies)

        # 2. Pure in-band single-frequency sine wave (low entropy)
        t = np.linspace(0, 1.0, 250)
        sine_wave = 15.0 * np.sin(2 * np.pi * 10 * t)  # 10 Hz sine
        spoof_signal = np.tile(sine_wave, (8, 1))
        anomalies = self.ids.analyze_signal(spoof_signal)
        self.assertIn("SPECTRAL_SPOOFING_ANOMALY", anomalies)

    def test_adc_amplifier_saturation(self):
        # 1. Nominal signal -> no saturation
        nominal_signal = np.random.normal(0, 15.0, (8, 250))
        out_nominal = self.twin.simulate_adc_saturation(nominal_signal)
        self.assertFalse(self.twin.amplifier_saturated)
        np.testing.assert_array_equal(out_nominal, nominal_signal)

        # 2. Oversized signal -> saturates and clips
        saturated_signal = np.random.normal(0, 15.0, (8, 250))
        saturated_signal[0, 10:20] = 1200.0  # Spike above rail
        saturated_signal[1, 50:60] = -1500.0  # Spike below rail

        out_saturated = self.twin.simulate_adc_saturation(saturated_signal)
        self.assertTrue(self.twin.amplifier_saturated)
        self.assertEqual(self.twin.hazard_state, "AMPLIFIER_SATURATED")
        self.assertEqual(self.twin.clinical_status, "Amplifier Saturation Error")
        
        # Verify clipping
        self.assertEqual(np.max(out_saturated), 1000.0)
        self.assertEqual(np.min(out_saturated), -1000.0)

if __name__ == "__main__":
    unittest.main()
