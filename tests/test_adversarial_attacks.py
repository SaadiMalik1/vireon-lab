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
from vireon.libraries.attack_factory.attack.adversarial import (
    AdversarialOptimizerAttack,
    TraceReplayAttack,
    RFJammingAttack,
    FramingDesynchronizationAttack,
    SessionReplayAttack,
    TemporalEvasionAttack
)
from vireon.runtime.twin import DigitalTwin

class MockDigitalTwin(DigitalTwin):
    def __init__(self):
        self.adc_vref = 4.5
        self.adc_gain = 24.0
        self.adc_resolution_bits = 24
        self.rf_packet_drop_rate = 0.0

    def get_state(self):
        return {"beta_power": 10.0}

def test_adversarial_optimizer():
    twin = MockDigitalTwin()
    rng = np.random.default_rng(42)
    attack = AdversarialOptimizerAttack(target_channels=[0], population_size=4, rng=rng)
    
    data = np.zeros((2, 250))
    # Evolve a few times
    for _ in range(6):
        out = attack.apply(data, eeg_channels=[0, 1], sample_rate=250, state_store=twin, rng=rng)
        assert out.shape == data.shape

def test_trace_replay(tmp_path):
    trace_file = tmp_path / "trace.csv"
    trace_file.write_text("1.0\n2.0\n3.0\n")
    
    twin = MockDigitalTwin()
    attack = TraceReplayAttack(target_channels=[1], trace_file_path=str(trace_file))
    
    data = np.zeros((2, 5))
    out = attack.apply(data, eeg_channels=[0, 1], sample_rate=250, state_store=twin)
    assert out.shape == data.shape
    # Check if trace is injected in channel 1
    np.testing.assert_array_equal(out[1, :], [1.0, 2.0, 3.0, 1.0, 2.0])

def test_rf_jamming():
    twin = MockDigitalTwin()
    attack = RFJammingAttack(drop_rate=0.8)
    data = np.zeros((2, 10))
    out = attack.apply(data, eeg_channels=[0], sample_rate=250, state_store=twin)
    assert twin.rf_packet_drop_rate == 0.8
    assert np.array_equal(out, data)

def test_framing_desynchronization():
    twin = MockDigitalTwin()
    attack = FramingDesynchronizationAttack(target_channels=[0], inject_start_byte=True)
    data = np.zeros((2, 10))
    out = attack.apply(data, eeg_channels=[0], sample_rate=250, state_store=twin)
    assert out.shape == data.shape
    assert out[0, 0] != 0.0

    attack2 = FramingDesynchronizationAttack(target_channels=[0], inject_start_byte=False)
    out2 = attack2.apply(data, eeg_channels=[0], sample_rate=250, state_store=twin)
    assert out2[0, 0] != 0.0

def test_session_replay():
    twin = MockDigitalTwin()
    attack = SessionReplayAttack(target_channels=[0], capture_duration_sec=0.01)
    data1 = np.ones((1, 5)) # 0.02s
    
    # Capture phase
    attack.apply(data1, eeg_channels=[0], sample_rate=250, state_store=twin)
    assert attack.is_capturing is False
    
    # Replay phase
    data2 = np.zeros((1, 5))
    out2 = attack.apply(data2, eeg_channels=[0], sample_rate=250, state_store=twin)
    assert np.array_equal(out2[0], np.ones(5))

def test_temporal_evasion():
    twin = MockDigitalTwin()
    rng = np.random.default_rng(42)
    attack = TemporalEvasionAttack(target_channels=[0], burst_duration_sec=0.01, quiet_duration_sec=0.01)
    
    data = np.zeros((2, 5)) # 0.02s
    out = attack.apply(data, eeg_channels=[0, 1], sample_rate=250, state_store=twin, rng=rng)
    assert out.shape == data.shape
