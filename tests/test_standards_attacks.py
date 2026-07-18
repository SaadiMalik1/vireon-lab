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
from vireon.core.attack_factory import AttackFactory
from vireon.core.threat_intel import ThreatIntelligence

class TestStandardAttacks(unittest.TestCase):
    def test_dynamic_attack_generation(self):
        # Verify registry loaded
        ti = ThreatIntelligence()
        self.assertGreater(len(ti.registry), 0, "Registry should load techniques from standards_mapping.json")

        # Test noise_injection attack
        attack_si = AttackFactory.create_dynamic_attack("noise_injection", target_channels=[0])
        self.assertEqual(attack_si.technique.get("stride"), "Tampering")
        
        twin = DigitalTwin(num_channels=8)
        clean_data = np.zeros((8, 100))
        mutated_data = attack_si.apply(clean_data, [0], 250, twin)
        
        # Channel 0 should have noise, others 0
        self.assertNotEqual(np.sum(np.abs(mutated_data[0, :])), 0.0)
        self.assertEqual(np.sum(np.abs(mutated_data[1, :])), 0.0)

        # Test DS (Denial of Service) attack -> signal_suppression
        attack_ds = AttackFactory.create_dynamic_attack("signal_suppression", target_channels=[0])
        self.assertEqual(attack_ds.technique.get("stride"), "Denial of Service")
        
        clean_data_high = np.ones((8, 100)) * 100.0
        mutated_ds_data = attack_ds.apply(clean_data_high, [0], 250, twin)
        
        # Channel 0 should be suppressed to 0
        self.assertEqual(np.sum(np.abs(mutated_ds_data[0, :])), 0.0)
        self.assertNotEqual(np.sum(np.abs(mutated_ds_data[1, :])), 0.0)

if __name__ == '__main__':
    unittest.main()
