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

from vireon.runtime.threat_intel import ThreatIntelligence
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
