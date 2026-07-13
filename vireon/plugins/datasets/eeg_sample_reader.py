import json
import os
import numpy as np
from typing import List, Dict, Any, Optional
from vireon.plugins.datasets import IDatasetReader

class EEGSampleReader(IDatasetReader):
    """
    Reads dataset metadata from datalake eeg-samples.json.
    Currently falls back to synthetic generation (like MockReader) if raw files aren't downloaded,
    but bridges the metadata into the VIREON pipeline.
    """
    def __init__(self, dataset_id: str = "adhd-mendeley-resting"):
        self.dataset_id = dataset_id
        self._sample_rate = 256
        self._num_channels = 4
        self._channel_names = ["TP9", "AF7", "AF8", "TP10"]
        self._metadata = {}
        
        # Load registry
        registry_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../neurosecurity/datalake/eeg-samples.json'))
        if os.path.exists(registry_path):
            with open(registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for s in data.get("samples", []):
                    if s["id"] == self.dataset_id:
                        self._metadata = s
                        self._sample_rate = s.get("samplingRateHz", 256)
                        self._num_channels = s.get("channels", 4)
                        # Just generate generic names if none exist
                        self._channel_names = [f"CH_{i}" for i in range(self._num_channels)]
                        break
                        
        self.position = 0

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def num_channels(self) -> int:
        return self._num_channels

    @property
    def total_samples(self) -> int:
        return -1

    @property
    def duration_sec(self) -> float:
        return -1.0

    @property
    def channel_names(self) -> List[str]:
        return self._channel_names

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata

    @property
    def supports_seeking(self) -> bool:
        return False

    def seek(self, sample_position: int) -> None:
        raise NotImplementedError("Streaming sample reader does not support seeking")

    def read_chunk(self, start_sample: int, num_samples: int) -> np.ndarray:
        # Fallback to generating synthetic data that matches the dataset metadata
        # In the future, this will use scipy.io to read .mat or mne to read .edf
        chunk = np.zeros((self._num_channels, num_samples))
        t = np.arange(self.position, self.position + num_samples) / self._sample_rate
        
        for ch in range(self._num_channels):
            # Alpha
            chunk[ch] += np.sin(2 * np.pi * 10 * t) * np.random.normal(0.8, 0.1)
            # Beta
            chunk[ch] += np.sin(2 * np.pi * 20 * t) * np.random.normal(0.4, 0.1)
            # Noise
            chunk[ch] += np.random.normal(0, 0.2, num_samples)
            
        self.position += num_samples
        return chunk
