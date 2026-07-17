import json
from unittest.mock import patch, mock_open
from vireon.plugins.datasets.eeg_sample_reader import EEGSampleReader

def test_eeg_sample_reader_default():
    reader = EEGSampleReader()
    
    # Defaults when file doesn't exist
    assert reader.sample_rate == 256
    assert reader.num_channels == 4
    assert reader.total_samples == -1
    assert reader.duration_sec == -1.0
    assert reader.channel_names == ["TP9", "AF7", "AF8", "TP10"]
    assert reader.metadata == {}
    assert reader.supports_seeking is False

def test_eeg_sample_reader_with_file():
    mock_registry = {
        "samples": [
            {
                "id": "test-dataset",
                "samplingRateHz": 500,
                "channels": 2,
                "name": "Test Data"
            }
        ]
    }
    
    mock_file_content = json.dumps(mock_registry)
    
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=mock_file_content)):
        
        reader = EEGSampleReader("test-dataset")
        
        assert reader.sample_rate == 500
        assert reader.num_channels == 2
        assert reader.channel_names == ["CH_0", "CH_1"]
        assert reader.metadata["name"] == "Test Data"

def test_eeg_sample_reader_read_chunk():
    reader = EEGSampleReader()
    
    chunk = reader.read_chunk(0, 100)
    assert chunk.shape == (4, 100)
    assert reader.position == 100
    
    # Read next chunk
    chunk2 = reader.read_chunk(100, 50)
    assert chunk2.shape == (4, 50)
    assert reader.position == 150

def test_eeg_sample_reader_seek():
    reader = EEGSampleReader()
    reader.position = 50
    
    # Should be a no-op
    reader.seek(100)
    assert reader.position == 50 # Unchanged because supports_seeking is False
