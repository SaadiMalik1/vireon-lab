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
from vireon_lab.engine.generators.jansen_rit import JansenRitNeuralMassGenerator, ColoredNoiseARGenerator

def test_jansen_rit_generator_shape():
    gen = JansenRitNeuralMassGenerator(num_channels=8)
    rng = np.random.default_rng(42)
    signals = gen.generate(num_samples=100, t_start=0.0, sampling_rate=100.0, rng=rng)
    
    assert signals.shape == (8, 100)
    assert not np.isnan(signals).any()
    assert not np.isinf(signals).any()

def test_colored_noise_generator_shape():
    gen = ColoredNoiseARGenerator(num_channels=4, alpha=0.85)
    rng = np.random.default_rng(42)
    signals = gen.generate(num_samples=50, t_start=0.0, sampling_rate=100.0, rng=rng)
    
    assert signals.shape == (4, 50)
    assert not np.isnan(signals).any()
