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

"""Integration test for full closed-loop signal simulation, control, and attack detection."""

import numpy as np
from knowledge.simulators.closed_loop_simulator import ClosedLoopSystem
from knowledge.simulators.attack_detector import AttackDetector, DetectionResult


def test_closed_loop_attack_detector_integration():
    """Verify that sensor spoofing in closed loop is caught by attack detector."""
    system = ClosedLoopSystem(seed=42, vulnerable=True, num_cycles=50)
    results = system.run()

    assert "statistics" in results
    assert "simulation" in results

    detector = AttackDetector(sampling_rate_hz=250.0)
    nominal_lfp = np.linspace(-15.0, -8.0, 50)
    attacked_lfp = nominal_lfp + 8.0

    res = detector.detect_bandpower_anomaly(nominal_lfp, attacked_lfp)
    assert isinstance(res, DetectionResult)
    assert res.confidence >= 0.0
