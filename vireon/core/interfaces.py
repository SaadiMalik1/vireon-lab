import abc
from typing import Any, List, Tuple, Dict, Optional
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
