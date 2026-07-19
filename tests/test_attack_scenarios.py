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
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vireon.runtime.twin import DigitalTwin
from vireon.runtime.event_bus import EventBus
from vireon.runtime.attack import SignalAttackEngine, AttackStep, AttackScenario
from vireon.runtime.plugin_registry import PluginRegistry, register_builtin_plugins


class TestAttackScenarios(unittest.TestCase):
    """Tests for composable and scripted attack scenarios with timing loops."""

    def setUp(self):
        self.twin = DigitalTwin(num_channels=8)
        self.bus = EventBus()
        self.attack_engine = SignalAttackEngine(self.twin, self.bus)
        self.registry = PluginRegistry()
        register_builtin_plugins(self.registry)

    def test_scenario_timeline(self):
        # 1. Define timed steps
        steps = [
            AttackStep(
                time_sec=1.0,
                attack_type="noise",
                duration_sec=2.0,
                target_channels=[0],
                params={"noise_level_microvolts": 75.0}
            ),
            AttackStep(
                time_sec=4.0,
                attack_type="suppression",
                duration_sec=1.5,
                target_channels=[1],
                params={"attenuation_factor": 0.01}
            )
        ]

        scenario = AttackScenario("test_scenario", steps, self.bus)

        # Track bus events
        event_topics = []
        self.bus.subscribe("*", lambda e: event_topics.append(e.topic))

        # 2. Assert initial state (t = 0.0)
        scenario.update(0.0, self.attack_engine, self.registry)
        self.assertEqual(len(self.attack_engine.modifiers), 0)

        # 3. Fast-forward to start of first step (t = 1.0)
        scenario.update(1.0, self.attack_engine, self.registry)
        self.assertEqual(len(self.attack_engine.modifiers), 1)
        self.assertEqual(self.attack_engine.modifiers[0].__class__.__name__, "NoiseInjectionAttack")
        self.assertEqual(self.attack_engine.modifiers[0].noise_level, 75.0)
        time.sleep(0.2)
        self.attack_engine.event_bus.flush()
        self.assertIn("attack.scenario_step.started", event_topics)

        # 4. Check middle of first step (t = 2.0)
        scenario.update(2.0, self.attack_engine, self.registry)
        self.assertEqual(len(self.attack_engine.modifiers), 1)

        # 5. Check end of first step (t = 3.0)
        scenario.update(3.0, self.attack_engine, self.registry)
        self.attack_engine.event_bus.flush()
        self.assertEqual(len(self.attack_engine.modifiers), 0)
        self.assertIn("attack.scenario_step.stopped", event_topics)

        # 6. Fast-forward to start of second step (t = 4.0)
        scenario.update(4.0, self.attack_engine, self.registry)
        self.assertEqual(len(self.attack_engine.modifiers), 1)
        self.assertEqual(self.attack_engine.modifiers[0].__class__.__name__, "SignalSuppressionAttack")
        self.assertEqual(self.attack_engine.modifiers[0].attenuation_factor, 0.01)

        # 7. Check expiration of second step (t = 5.5)
        scenario.update(5.5, self.attack_engine, self.registry)
        self.assertEqual(len(self.attack_engine.modifiers), 0)


if __name__ == "__main__":
    unittest.main()
