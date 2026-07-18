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
from vireon_lab.providers.datasets.mne_reader import MNEReader

def test_mne_reader_fallback_no_file():
    # If file doesn't exist and fallback is True, it should use MockEEGReader
    reader = MNEReader("nonexistent.vhdr", fallback_on_error=True)
    assert reader.mock_reader is not None
    assert reader.supports_seeking is True
    
    # Check properties pass through to mock_reader
    assert reader.sample_rate == 250
    assert reader.num_channels == 8
    assert reader.total_samples == -1
    assert reader.duration_sec == -1.0
    assert len(reader.channel_names) == 8
    assert "type" in reader.metadata
    
    # Read chunk from mock
    data = reader.read_chunk(0, 100)
    assert data.shape == (8, 100)
    
    # Seek
    reader.seek(10)
    
def test_mne_reader_no_fallback_raises():
    with pytest.raises(Exception):
        MNEReader("nonexistent.vhdr", fallback_on_error=False)

def test_mne_reader_various_extensions():
    # These will all hit the Exception block because files don't exist
    reader1 = MNEReader("test.set", fallback_on_error=True)
    reader2 = MNEReader("test.edf", fallback_on_error=True)
    reader3 = MNEReader("test.txt", fallback_on_error=True)
    
    assert reader1.mock_reader is not None
    assert reader2.mock_reader is not None
    assert reader3.mock_reader is not None

def test_mne_reader_without_mne(monkeypatch):
    import vireon_lab.providers.datasets.mne_reader
    monkeypatch.setattr(vireon_lab.providers.datasets.mne_reader, 'HAS_MNE', False)
    
    reader = MNEReader("test.vhdr", fallback_on_error=True)
    assert reader.mock_reader is not None

    with pytest.raises(ImportError):
        MNEReader("test.vhdr", fallback_on_error=False)

def test_mne_reader_read_chunk_no_raw():
    reader = MNEReader("test.vhdr", fallback_on_error=True)
    # forcefully remove mock to test no raw path
    reader.mock_reader = None
    reader.raw = None
    data = reader.read_chunk(0, 10)
    assert np.all(data == 0.0)
    assert data.shape == (8, 10)
