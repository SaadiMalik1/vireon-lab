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

import pytest
import numpy as np
from vireon.runtime.twin import DigitalTwin
from vireon.libraries.attack_factory.attack.physical import (
    ElectrodeSaturationAttack,
    PacketLossAttack,
    TimingJitterAttack,
    DropoutAttack,
    ClippingAttack,
    AmplifierSaturationAttack,
    EMIAttack,
    MotionArtifactAttack,
    CrossTalkAttack,
    ClockSkewAttack
)

@pytest.fixture
def dummy_data():
    return np.zeros((4, 100))

@pytest.fixture
def twin():
    return DigitalTwin(num_channels=4)

def test_electrode_saturation(dummy_data, twin):
    attack = ElectrodeSaturationAttack(target_channels=[0, 1])
    out = attack.apply(dummy_data, [0, 1, 2, 3], 250, twin)
    assert np.all(out[0, :] == 1e6)
    assert np.all(out[2, :] == 0.0)

def test_packet_loss(dummy_data, twin):
    rng = np.random.default_rng(42)
    attack = PacketLossAttack(target_channels=[0], drop_prob=1.0) # Always drop
    dummy_data[0, :] = 5.0
    out = attack.apply(dummy_data, [0, 1], 250, twin, rng=rng)
    assert np.all(out[0, :] == 0.0)

def test_timing_jitter(dummy_data, twin):
    attack = TimingJitterAttack(target_channels=[0], jitter_ms=4.0) # 1 sample at 250Hz
    dummy_data[0, 0] = 5.0
    out = attack.apply(dummy_data, [0], 250, twin)
    assert out[0, 1] == 5.0 # Shifted by 1
    
def test_dropout(dummy_data, twin):
    rng = np.random.default_rng(42)
    attack = DropoutAttack(target_channels=[0], dropout_length_sec=0.1) # 25 samples
    dummy_data[0, :] = 5.0
    out = attack.apply(dummy_data, [0], 250, twin, rng=rng)
    assert np.any(out[0, :] == 0.0)
    assert np.any(out[0, :] == 5.0)

def test_clipping(dummy_data, twin):
    attack = ClippingAttack(target_channels=[0], clip_value=10.0)
    dummy_data[0, :] = 20.0
    out = attack.apply(dummy_data, [0], 250, twin)
    assert np.all(out[0, :] == 10.0)

def test_amplifier_saturation(dummy_data, twin):
    attack = AmplifierSaturationAttack(target_channels=[0])
    dummy_data[0, 0:50] = 1.0
    dummy_data[0, 50:100] = -1.0
    out = attack.apply(dummy_data, [0], 250, twin)
    assert np.all(out[0, 0:50] == 500.0)
    assert np.all(out[0, 50:100] == -500.0)

def test_emi(dummy_data, twin):
    attack = EMIAttack(target_channels=[0])
    out = attack.apply(dummy_data, [0], 250, twin)
    assert np.any(out[0, :] != 0.0)

def test_motion_artifact(dummy_data, twin):
    rng = np.random.default_rng(42)
    attack = MotionArtifactAttack(target_channels=[0])
    out = attack.apply(dummy_data, [0], 250, twin, rng=rng)
    assert np.any(out[0, :] != 0.0)

def test_cross_talk(dummy_data, twin):
    attack = CrossTalkAttack(target_channels=[1], source_channel=0, crosstalk_factor=0.5)
    dummy_data[0, :] = 10.0
    out = attack.apply(dummy_data, [0, 1], 250, twin)
    assert np.all(out[1, :] == 5.0)

def test_clock_skew(dummy_data, twin):
    attack = ClockSkewAttack(target_channels=[0], skew_rate=0.01)
    dummy_data[0, :] = np.arange(100)
    out = attack.apply(dummy_data, [0], 250, twin)
    assert out[0, 99] == 99.0
