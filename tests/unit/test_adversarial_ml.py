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

import numpy as np
from vireon_lab.scenarios.adversarial_ml import (
    FGSMAttack,
    PGDAttack,
    CWAttack,
    BackdoorTriggerInjector
)
from vireon.runtime.twin import DigitalTwin

def test_fgsm_attack():
    twin = DigitalTwin(num_channels=8)
    attack = FGSMAttack(target_channels=[0], epsilon=10.0)
    
    # Generate a simple signal
    data = np.ones((2, 100))
    data[0, :50] = -1.0 # First half negative, second half positive
    
    mutated = attack.apply(data, eeg_channels=[0, 1], sample_rate=250, state_store=twin)
    
    # For FGSM, gradient_sign is np.sign(data)
    # mutated should be data + epsilon * sign(data)
    # data is -1.0 -> sign is -1.0 -> mutated is -1.0 + 10.0 * (-1.0) = -11.0
    # data is 1.0 -> sign is 1.0 -> mutated is 1.0 + 10.0 * 1.0 = 11.0
    assert np.allclose(mutated[0, :50], -11.0)
    assert np.allclose(mutated[0, 50:], 11.0)
    # Channel 1 is not targeted
    assert np.array_equal(mutated[1, :], data[1, :])

def test_pgd_attack():
    twin = DigitalTwin(num_channels=8)
    attack = PGDAttack(target_channels=[1], epsilon=15.0, alpha=2.0, steps=5)
    
    data = np.zeros((2, 100))
    data[1, :] = 5.0
    
    mutated = attack.apply(data, eeg_channels=[0, 1], sample_rate=250, state_store=twin)
    
    # Original is 5.0, sign is 1.0
    # Iterations will add alpha (2.0) and clip to original + epsilon (5.0 + 15.0 = 20.0)
    # 5 steps of 2.0 = +10.0. So mutated will be 15.0
    assert np.allclose(mutated[1, :], 15.0)
    assert np.array_equal(mutated[0, :], data[0, :])

def test_cw_attack():
    twin = DigitalTwin(num_channels=8)
    attack = CWAttack(target_channels=[0], target_frequency_hz=6.0, target_amplitude_uv=6.0)
    
    data = np.zeros((2, 100))
    mutated = attack.apply(data, eeg_channels=[0, 1], sample_rate=250, state_store=twin)
    
    # Should inject a sine wave
    assert not np.allclose(mutated[0, :], 0)
    assert np.allclose(mutated[1, :], 0)
    
    # Check that phase is updated by calling it again
    mutated2 = attack.apply(data, eeg_channels=[0, 1], sample_rate=250, state_store=twin)
    assert not np.allclose(mutated[0, :], mutated2[0, :])

def test_backdoor_trigger_injector():
    twin = DigitalTwin(num_channels=8)
    attack = BackdoorTriggerInjector(target_channels=[0], trigger_frequency_hz=21.0, trigger_amplitude_uv=30.0)
    
    data = np.zeros((2, 100))
    mutated = attack.apply(data, eeg_channels=[0, 1], sample_rate=250, state_store=twin)
    
    # Should inject a 20Hz sine wave
    assert not np.allclose(mutated[0, :], 0)
    assert np.allclose(mutated[1, :], 0)
    
    # Phase update check
    mutated2 = attack.apply(data, eeg_channels=[0, 1], sample_rate=250, state_store=twin)
    assert not np.allclose(mutated[0, :], mutated2[0, :])
