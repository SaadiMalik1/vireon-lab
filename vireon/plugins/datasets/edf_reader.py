import numpy as np
from typing import List, Dict, Any
from vireon.plugins.datasets import IDatasetReader
from vireon.plugins.datasets.mock_reader import MockEEGReader
import logging

logger = logging.getLogger(__name__)

try:
    import pyedflib
    HAS_PYEDFLIB = True
except ImportError:
    HAS_PYEDFLIB = False


class EDFReader(IDatasetReader):
    """
    Reader for European Data Format (EDF/BDF) files.
    Relies on pyedflib (a C-extension wrapper). Falls back gracefully 
    to MockEEGReader if pyedflib is not installed or if the file is missing/invalid.
    """

    def __init__(self, file_path: str, fallback_on_error: bool = True):
        self.file_path = file_path
        self.fallback_on_error = fallback_on_error
        self.reader = None
        self._sample_rate = 250
        self._num_channels = 8
        self.mock_reader = None

        self._channel_names: List[str] = []
        self._total_samples = 0
        self._duration_sec = 0.0
        self._metadata: Dict[str, Any] = {}

        if not HAS_PYEDFLIB:
            if fallback_on_error:
                logger.warning("pyedflib not installed. Falling back to MockEEGReader.")
                self.mock_reader = MockEEGReader(self._sample_rate, self._num_channels)
            else:
                raise ImportError("pyedflib is required to read EDF files but was not found.")
        else:
            try:
                self.reader = pyedflib.EdfReader(file_path)
                self._sample_rate = int(self.reader.getSampleFrequency(0))
                self._num_channels = self.reader.signals_in_file
                self._total_samples = self.reader.getNSamples()[0]
                self._duration_sec = float(self.reader.getFileDuration())
                self._channel_names = [self.reader.getLabel(i).strip() for i in range(self._num_channels)]

                # Extract rich metadata
                self._metadata = {
                    "file_path": file_path,
                    "patient_name": self.reader.getPatientName().strip(),
                    "patient_code": self.reader.getPatientCode().strip(),
                    "gender": self.reader.getGender().strip(),
                    "birthdate": str(self.reader.getBirthdate()).strip(),
                    "start_datetime": str(self.reader.getStartdatetime()),
                    "duration_sec": self._duration_sec,
                    "total_samples": self._total_samples,
                }
            except Exception as e:
                if fallback_on_error:
                    logger.error(f"Error reading {file_path}. Falling back to MockEEGReader.", exc_info=True)
                    self.mock_reader = MockEEGReader(self._sample_rate, self._num_channels)
                else:
                    raise e

    @property
    def sample_rate(self) -> int:
        if self.mock_reader:
            return self.mock_reader.sample_rate
        return self._sample_rate

    @property
    def num_channels(self) -> int:
        if self.mock_reader:
            return self.mock_reader.num_channels
        return self._num_channels

    @property
    def total_samples(self) -> int:
        if self.mock_reader:
            return self.mock_reader.total_samples
        return self._total_samples

    @property
    def duration_sec(self) -> float:
        if self.mock_reader:
            return self.mock_reader.duration_sec
        return self._duration_sec

    @property
    def channel_names(self) -> List[str]:
        if self.mock_reader:
            return self.mock_reader.channel_names
        return self._channel_names

    @property
    def metadata(self) -> Dict[str, Any]:
        if self.mock_reader:
            return self.mock_reader.metadata
        return self._metadata

    @property
    def supports_seeking(self) -> bool:
        return True

    def seek(self, sample_position: int) -> None:
        if self.mock_reader:
            self.mock_reader.seek(sample_position)
            return

        if sample_position < 0 or sample_position >= self._total_samples:
            raise ValueError(f"Sample position {sample_position} out of bounds for total_samples {self._total_samples}")
        # Note: pyedflib does not maintain a read pointer for readSignal;
        # read_chunk specifies start_sample directly.

    def read_chunk(self, start_sample: int, num_samples: int) -> np.ndarray:
        if self.mock_reader:
            return self.mock_reader.read_chunk(start_sample, num_samples)

        # Read from real EDF file
        data = np.zeros((self._num_channels, num_samples))
        for ch in range(self._num_channels):
            try:
                # readSignal returns float64 array of values in microvolts
                data[ch, :] = self.reader.readSignal(ch, start_sample, num_samples)
            except Exception as e:
                # Handle end of file or read errors by zeroing
                logger.error(f"EDF read error on channel {ch}: {e}", exc_info=True)
                data[ch, :] = 0.0
        return data

    def __del__(self):
        if self.reader:
            try:
                self.reader.close()
            except Exception:
                logger.debug("Failed to close EDF reader", exc_info=True)
