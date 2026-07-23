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

"""
Example showing how to create and register a custom VIREON attack plugin.
"""
from vireon.runtime.attack import ISignalModifier
import numpy as np
from typing import List, Optional
from vireon.runtime.twin import DigitalTwin

class CustomBatteryDrainAttack(ISignalModifier):
    def __init__(self, drain_rate=50.0):
        self.drain_rate = drain_rate

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        print(f"Applying custom battery drain attack with rate {self.drain_rate}...")
        twin.battery_level = max(0.0, twin.battery_level - self.drain_rate)
        return data

def get_plugin_info():
    """
    Entry point for the plugin system.
    """
    return {
        "name": "CustomBatteryDrain",
        "description": "Drains the battery by flooding the BLE interface",
        "class": CustomBatteryDrainAttack,
        "type": "attack"
    }

if __name__ == "__main__":
    print("This is a VIREON plugin. Register it via pyproject.toml entry-points or load dynamically.")
