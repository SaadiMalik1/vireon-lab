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
from vireon_lab.engine.circular_buffer import CircularBuffer

def test_circular_buffer_basic_write_read():
    cb = CircularBuffer(num_channels=4, capacity_samples=100)
    data = np.ones((4, 20)) * 5.0
    cb.write(data)
    
    assert cb.total_written == 20
    out = cb.read_last(20)
    assert out.shape == (4, 20)
    assert np.allclose(out, 5.0)

def test_circular_buffer_wrap_around():
    cb = CircularBuffer(num_channels=2, capacity_samples=10)
    
    # Write 8 samples
    data1 = np.ones((2, 8)) * 1.0
    cb.write(data1)
    
    # Write 5 more samples (triggers wrap-around)
    data2 = np.ones((2, 5)) * 2.0
    cb.write(data2)
    
    assert cb.total_written == 13
    out = cb.read_last(10)
    assert out.shape == (2, 10)
    # The oldest 3 samples should be 1.0, and the newest 5 should be 2.0
    assert np.allclose(out[:, :5], 1.0)
    assert np.allclose(out[:, 5:], 2.0)

def test_circular_buffer_reset():
    cb = CircularBuffer(num_channels=2, capacity_samples=50)
    cb.write(np.ones((2, 25)))
    cb.reset()
    
    assert cb.total_written == 0
    assert cb.write_pos == 0
    assert cb.read_last(10).shape == (2, 0)
