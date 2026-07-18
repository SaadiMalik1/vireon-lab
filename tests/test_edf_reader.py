import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from vireon_lab.providers.datasets.edf_reader import EDFReader

@pytest.fixture
def mock_pyedflib():
    with patch("vireon_lab.providers.datasets.edf_reader.pyedflib", create=True) as mock_lib:
        mock_reader = MagicMock()
        mock_reader.getSampleFrequency.return_value = 250
        mock_reader.signals_in_file = 2
        mock_reader.getNSamples.return_value = [1000]
        mock_reader.getFileDuration.return_value = 4.0
        mock_reader.getLabel.side_effect = ["CH1", "CH2"]
        mock_reader.getPatientName.return_value = "Test Patient"
        mock_reader.getPatientCode.return_value = "P001"
        mock_reader.getGender.return_value = "F"
        mock_reader.getBirthdate.return_value = "01-01-1990"
        mock_reader.getStartdatetime.return_value = "2023-01-01"
        mock_reader.readSignal.return_value = np.ones(10)
        
        mock_lib.EdfReader.return_value = mock_reader
        yield mock_lib

def test_edf_reader_with_pyedflib(mock_pyedflib, monkeypatch):
    monkeypatch.setattr("vireon_lab.providers.datasets.edf_reader.HAS_PYEDFLIB", True, raising=False)
    reader = EDFReader("test.edf")
    
    assert reader.sample_rate == 250
    assert reader.num_channels == 2
    assert reader.total_samples == 1000
    assert reader.duration_sec == 4.0
    assert reader.channel_names == ["CH1", "CH2"]
    assert reader.metadata["patient_name"] == "Test Patient"
    assert reader.supports_seeking is True
    
    # Seeking shouldn't throw error
    reader.seek(500)
    
    with pytest.raises(ValueError):
        reader.seek(-1)
        
    with pytest.raises(ValueError):
        reader.seek(2000)
        
    chunk = reader.read_chunk(0, 10)
    assert chunk.shape == (2, 10)
    assert np.all(chunk == 1.0)
    
    # Trigger read error
    mock_pyedflib.EdfReader.return_value.readSignal.side_effect = Exception("Read Error")
    chunk_err = reader.read_chunk(0, 10)
    assert np.all(chunk_err == 0.0)

def test_edf_reader_without_pyedflib(monkeypatch):
    monkeypatch.setattr("vireon_lab.providers.datasets.edf_reader.HAS_PYEDFLIB", False, raising=False)
    
    # Should fallback to mock reader
    reader = EDFReader("test.edf", fallback_on_error=True)
    assert reader.mock_reader is not None
    assert reader.sample_rate == 250
    assert reader.num_channels == 8
    
    # Check properties delegating to mock reader
    assert reader.total_samples == -1 # mock reader default
    assert reader.channel_names == [f"Ch{i}" for i in range(8)]
    assert isinstance(reader.metadata, dict)
    
    chunk = reader.read_chunk(0, 10)
    assert chunk.shape == (8, 10)
    
    # Test seeking delegation
    reader.seek(100) # Should not raise

def test_edf_reader_without_pyedflib_no_fallback(monkeypatch):
    monkeypatch.setattr("vireon_lab.providers.datasets.edf_reader.HAS_PYEDFLIB", False, raising=False)
    
    with pytest.raises(ImportError):
        EDFReader("test.edf", fallback_on_error=False)

def test_edf_reader_exception_during_init(mock_pyedflib, monkeypatch):
    monkeypatch.setattr("vireon_lab.providers.datasets.edf_reader.HAS_PYEDFLIB", True, raising=False)
    mock_pyedflib.EdfReader.side_effect = Exception("Init Error")
    
    # Should fallback
    reader = EDFReader("test.edf", fallback_on_error=True)
    assert reader.mock_reader is not None
    
    # No fallback
    with pytest.raises(Exception, match="Init Error"):
        EDFReader("test.edf", fallback_on_error=False)
