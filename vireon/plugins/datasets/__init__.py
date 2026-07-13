from abc import ABC, abstractmethod
from typing import List, Dict, Any
import numpy as np


class IDatasetReader(ABC):
    """
    Standard interface for all dataset readers in VIREON.

    Allows streaming neural signals from files (EDF/BDF/CSV/FIF), remote
    repositories, or synthetic signal generators.
    """

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """Returns the recording sample rate in Hz."""
        pass

    @property
    @abstractmethod
    def num_channels(self) -> int:
        """Returns the number of EEG channels present."""
        pass

    @property
    @abstractmethod
    def total_samples(self) -> int:
        """Returns the total number of samples, or -1 if streaming/infinite."""
        pass

    @property
    @abstractmethod
    def duration_sec(self) -> float:
        """Returns the total duration in seconds, or -1.0 if streaming/infinite."""
        pass

    @property
    @abstractmethod
    def channel_names(self) -> List[str]:
        """Returns the names/labels of the channels."""
        pass

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Returns metadata about the recording (patient info, date, etc.)."""
        pass

    @property
    @abstractmethod
    def supports_seeking(self) -> bool:
        """Returns True if seek() is supported."""
        pass

    @abstractmethod
    def seek(self, sample_position: int) -> None:
        """
        Set the read position to a specific sample index.

        Raises:
            NotImplementedError: If supports_seeking is False.
            ValueError: If sample_position is out of bounds.
        """
        pass

    @abstractmethod
    def read_chunk(self, start_sample: int, num_samples: int) -> np.ndarray:
        """
        Reads a 2D numpy array representing neural signals.
        Returns array of shape (num_channels, num_samples).
        """
        pass
