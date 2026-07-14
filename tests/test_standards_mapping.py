from vireon.core.threat_intel import ThreatIntelligence
import unittest

class TestStandardsMapping(unittest.TestCase):
    def test_threat_intel_lookup(self):
        ti = ThreatIntelligence()
        result = ti.resolve_attack("noise_injection")
        self.assertIsNotNone(result)
        self.assertEqual(result["stride"], "Tampering")
        self.assertTrue("CWE" in result["cwe"])
        
    def test_invalid_lookup(self):
        ti = ThreatIntelligence()
        result = ti.resolve_attack("nonexistent_attack")
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
