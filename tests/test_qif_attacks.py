import unittest
import numpy as np
from vireon.core.twin import DigitalTwin
from vireon.core.attack_factory import AttackFactory
from vireon.plugins.clinical.qif_registry import QIFRegistry

class TestQIFAttacks(unittest.TestCase):
    def test_dynamic_attack_generation(self):
        # Verify registry loaded
        registry = QIFRegistry()
        techniques = registry.get_all_techniques()
        self.assertGreater(len(techniques), 0, "Registry should load techniques from qif.json")

        # Test SI (Signal Injection) attack (e.g., QIF-T0001)
        # Assuming QIF-T0001 is SI
        attack_si = AttackFactory.create_from_qif("QIF-T0001", target_channels=[0])
        self.assertEqual(attack_si.technique.category, "SI")
        
        twin = DigitalTwin(num_channels=8)
        clean_data = np.zeros((8, 100))
        mutated_data = attack_si.apply(clean_data, [0], 250, twin)
        
        # Channel 0 should have noise, others 0
        self.assertNotEqual(np.sum(np.abs(mutated_data[0, :])), 0.0)
        self.assertEqual(np.sum(np.abs(mutated_data[1, :])), 0.0)
        self.assertTrue("QIF-T0001" in twin.clinical_status)

        # Test DS (Denial of Service) attack (e.g., QIF-T0002)
        attack_ds = AttackFactory.create_from_qif("QIF-T0002", target_channels=[0])
        self.assertEqual(attack_ds.technique.category, "DS")
        
        clean_data_high = np.ones((8, 100)) * 100.0
        mutated_ds_data = attack_ds.apply(clean_data_high, [0], 250, twin)
        
        # Channel 0 should be suppressed to 0
        self.assertEqual(np.sum(np.abs(mutated_ds_data[0, :])), 0.0)
        self.assertNotEqual(np.sum(np.abs(mutated_ds_data[1, :])), 0.0)

if __name__ == '__main__':
    unittest.main()
