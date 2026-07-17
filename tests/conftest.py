import pytest
import os
import sys

# Ensure vireon is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vireon.core.twin import DigitalTwin
from vireon.core.config import ExperimentConfig

@pytest.fixture
def mock_twin():
    """A standard DigitalTwin instance for testing."""
    twin = DigitalTwin(device_id="TEST-VIRT-EEG-01", sample_rate=250, num_channels=8, seed=42)
    return twin

@pytest.fixture
def mock_config():
    """A standard ExperimentConfig for testing."""
    return ExperimentConfig.model_validate({
        "duration_sec": 1.0,
        "device": {
            "device_id": "TEST-VIRT-EEG-01",
            "sample_rate": 250,
            "num_channels": 8
        },
        "attacks": {
            "active": ["noise"]
        }
    })
