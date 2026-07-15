import abc
from typing import Any, List
import numpy as np

class ITwin(abc.ABC):
    sample_rate: int
    num_channels: int
    physics_engine: Any
    neural_dynamics: Any
    stimulation_amplitude_ma: float
    stimulation_frequency_hz: float
    hazard_state: str
    connected: bool

    @abc.abstractmethod
    def get_sim_clock(self) -> float:
        pass
        
    @abc.abstractmethod
    def snapshot(self) -> dict:
        pass
        
    @abc.abstractmethod
    def restore(self, snap: dict):
        pass

    @abc.abstractmethod
    def set_sim_clock(self, clock: float):
        pass


class IDetector(abc.ABC):
    @abc.abstractmethod
    def score_signal(self, data: np.ndarray) -> float:
        pass
        
    @abc.abstractmethod
    def analyze_signal(self, data: np.ndarray) -> List[str]:
        pass

class ICryptoChannel(abc.ABC):
    @abc.abstractmethod
    def encrypt_data(self, plaintext: bytes) -> bytes:
        pass
        
    @abc.abstractmethod
    def decrypt_data(self, ciphertext: bytes) -> bytes:
        pass

class ITransport(abc.ABC):
    @abc.abstractmethod
    def send(self, data: Any):
        pass
        
    @abc.abstractmethod
    def receive(self) -> Any:
        pass
