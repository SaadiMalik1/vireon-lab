import abc
from typing import Any, List
import numpy as np

class ITwin(abc.ABC):
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

    @property
    @abc.abstractmethod
    def sample_rate(self) -> int:
        pass

    @sample_rate.setter
    @abc.abstractmethod
    def sample_rate(self, value: int):
        pass

    @property
    @abc.abstractmethod
    def num_channels(self) -> int:
        pass

    @num_channels.setter
    @abc.abstractmethod
    def num_channels(self, value: int):
        pass

    @property
    @abc.abstractmethod
    def physics_engine(self) -> Any:
        pass

    @physics_engine.setter
    @abc.abstractmethod
    def physics_engine(self, value: Any):
        pass

    @property
    @abc.abstractmethod
    def neural_dynamics(self) -> Any:
        pass

    @neural_dynamics.setter
    @abc.abstractmethod
    def neural_dynamics(self, value: Any):
        pass

    @property
    @abc.abstractmethod
    def stimulation_amplitude_ma(self) -> float:
        pass

    @stimulation_amplitude_ma.setter
    @abc.abstractmethod
    def stimulation_amplitude_ma(self, value: float):
        pass

    @property
    @abc.abstractmethod
    def stimulation_frequency_hz(self) -> float:
        pass

    @stimulation_frequency_hz.setter
    @abc.abstractmethod
    def stimulation_frequency_hz(self, value: float):
        pass

    @property
    @abc.abstractmethod
    def hazard_state(self) -> str:
        pass

    @hazard_state.setter
    @abc.abstractmethod
    def hazard_state(self, value: str):
        pass

    @property
    @abc.abstractmethod
    def connected(self) -> bool:
        pass

    @connected.setter
    @abc.abstractmethod
    def connected(self, value: bool):
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
