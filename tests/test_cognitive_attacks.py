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
from vireon.runtime.twin import DigitalTwin
from vireon.runtime.attack.cognitive import (
    NeuroPhishingAttack,
    FirmwareRollbackAttack,
    InsiderThreatAttack
)

def test_neuro_phishing_attack_emotional():
    twin = DigitalTwin(num_channels=8)
    attack = NeuroPhishingAttack(target_channels=[0, 1], manipulation_type="emotional")
    
    data = np.zeros((8, 100))
    eeg_channels = [0, 1, 2, 3, 4, 5, 6, 7]
    sample_rate = 100
    
    mutated = attack.apply(data, eeg_channels, sample_rate, twin)
    
    # Should inject a 10 Hz sine wave into channels 0 and 1
    assert not np.allclose(mutated[0, :], 0)
    assert not np.allclose(mutated[1, :], 0)
    assert np.allclose(mutated[2, :], 0) # Untargeted
    
    # Twin state should be updated
    assert twin.clinical_alert_active is True
    assert "emotional" in twin.clinical_status.lower()
    assert twin.dsm5_diagnosis == "INDUCED_MANIA"
    assert twin.diagnostic_cluster == "COGNITIVE_WARFARE"

def test_neuro_phishing_attack_bci():
    twin = DigitalTwin(num_channels=8)
    attack = NeuroPhishingAttack(target_channels=[3], manipulation_type="bci_hijack")
    
    data = np.zeros((8, 100))
    mutated = attack.apply(data, [3], 100, twin)
    
    assert not np.allclose(mutated[3, :], 0)
    assert twin.clinical_alert_active is True
    assert "bci_hijack" in twin.clinical_status.lower()

def test_firmware_rollback_attack():
    twin = DigitalTwin(num_channels=8)
    attack = FirmwareRollbackAttack(target_channels=[], payload_version=0)
    
    # Check payload property
    payload = attack.full_payload
    assert len(payload) > 600000
    
    data = np.zeros((8, 10))
    mutated = attack.apply(data, [], 100, twin)
    
    # It shouldn't mutate data
    assert np.array_equal(data, mutated)
    assert attack.has_fired is True
    assert twin.clinical_alert_active is True
    assert "OTA Downgrade Attempted" in twin.clinical_status
    
    # Calling apply again shouldn't fire again
    mutated2 = attack.apply(data, [], 100, twin)
    assert np.array_equal(data, mutated2)
    
    # Revert
    attack.revert(twin)
    assert twin.clinical_alert_active is False
    assert twin.clinical_status == "Nominal"

def test_insider_threat_attack():
    twin = DigitalTwin(num_channels=8)
    twin.stimulation_amplitude_ma = 5.0
    attack = InsiderThreatAttack(target_channels=[])
    
    data = np.zeros((8, 10))
    mutated = attack.apply(data, [], 100, twin)
    
    assert np.array_equal(data, mutated)
    assert twin.stimulation_amplitude_ma == 15.0
    assert twin.clinical_alert_active is True
    assert attack.has_fired is True
    
    # Revert
    attack.revert(twin)
    assert twin.stimulation_amplitude_ma == 5.0
    assert twin.clinical_alert_active is False
