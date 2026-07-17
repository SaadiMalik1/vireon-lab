import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from vireon.plugins.datasets.fif_reader import FIFReader

@pytest.fixture
def mock_mne():
    with patch("vireon.plugins.datasets.fif_reader.mne", create=True) as mock_mne_lib:
        mock_raw = MagicMock()
        mock_raw.info = {"sfreq": 250, "subject_info": "SUBJ1", "device_info": "DEV1"}
        mock_raw.ch_names = ["CH1", "CH2"]
        mock_raw.n_times = 1000
        mock_raw.times = [0.0, 1.0, 2.0, 4.0]
        
        # Mock __getitem__ for raw[:, start:stop]
        def mock_getitem(item):
            start = item[1].start or 0
            stop = item[1].stop or 1000
            length = stop - start
            return np.ones((2, length)) * 1e-6, None # returns tuple (data, times)
            
        mock_raw.__getitem__.side_effect = mock_getitem
        
        mock_mne_lib.io.read_raw_fif.return_value = mock_raw
        yield mock_mne_lib

def test_fif_reader_with_mne(mock_mne, monkeypatch):
    monkeypatch.setattr("vireon.plugins.datasets.fif_reader.HAS_MNE", True, raising=False)
    reader = FIFReader("test.fif")
    
    assert reader.sample_rate == 250
    assert reader.num_channels == 2
    assert reader.total_samples == 1000
    assert reader.duration_sec == 4.0
    assert reader.channel_names == ["CH1", "CH2"]
    assert reader.metadata["subject_id"] == "SUBJ1"
    assert reader.supports_seeking is True
    
    # Seeking
    reader.seek(500)
    
    with pytest.raises(ValueError):
        reader.seek(-1)
        
    with pytest.raises(ValueError):
        reader.seek(2000)
        
    chunk = reader.read_chunk(0, 10)
    assert chunk.shape == (2, 10)
    assert np.all(chunk == 1.0) # 1e-6 * 1e6
    
    # Wrap around reading
    chunk_wrap = reader.read_chunk(995, 10)
    assert chunk_wrap.shape == (2, 10)
    assert np.all(chunk_wrap == 1.0)
    
    # Exception handling during read
    mock_mne.io.read_raw_fif.return_value.__getitem__.side_effect = Exception("Read error")
    chunk_err = reader.read_chunk(0, 10)
    assert np.all(chunk_err == 0.0)

def test_fif_reader_without_mne(monkeypatch):
    monkeypatch.setattr("vireon.plugins.datasets.fif_reader.HAS_MNE", False, raising=False)
    
    # Should fallback to mock reader
    reader = FIFReader("test.fif", fallback_on_error=True)
    assert reader.mock_reader is not None
    assert reader.sample_rate == 250
    assert reader.num_channels == 8
    
    # Check properties delegating to mock reader
    assert reader.total_samples == -1 # mock reader default
    assert reader.channel_names == [f"Ch{i}" for i in range(8)]
    assert isinstance(reader.metadata, dict)
    
    chunk = reader.read_chunk(0, 10)
    assert chunk.shape == (8, 10)
    
    reader.seek(100) # Should not raise

def test_fif_reader_without_mne_no_fallback(monkeypatch):
    monkeypatch.setattr("vireon.plugins.datasets.fif_reader.HAS_MNE", False, raising=False)
    
    with pytest.raises(ImportError):
        FIFReader("test.fif", fallback_on_error=False)

def test_fif_reader_exception_during_init(mock_mne, monkeypatch):
    monkeypatch.setattr("vireon.plugins.datasets.fif_reader.HAS_MNE", True, raising=False)
    mock_mne.io.read_raw_fif.side_effect = Exception("Init Error")
    
    # Should fallback
    reader = FIFReader("test.fif", fallback_on_error=True)
    assert reader.mock_reader is not None
    
    # No fallback
    with pytest.raises(Exception, match="Init Error"):
        FIFReader("test.fif", fallback_on_error=False)
