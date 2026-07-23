# Copyright 2026 VIREON Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from abc import ABC, abstractmethod
import numpy as np

class ISignalGenerator(ABC):
    """Abstract Base Class for neural signal generators."""
    
    @abstractmethod
    def generate(self, num_samples: int, t_start: float, sampling_rate: float, rng: np.random.Generator) -> np.ndarray:
        """
        Generates signal matrix of shape (num_channels, num_samples).
        """
        pass


class IArtifactInjector(ABC):
    """Abstract Base Class for physiological artifact injectors."""
    
    @abstractmethod
    def inject(self, signals: np.ndarray, t_axis: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """
        Injects physiological artifacts (e.g. eye blinks, EMG, ECG) into signals array.
        """
        pass


class IAttackMutator(ABC):
    """Abstract Base Class for physical threat mutators."""
    
    @abstractmethod
    def mutate(self, signals: np.ndarray, t_axis: np.ndarray, intensity: float, rng: np.random.Generator) -> np.ndarray:
        """
        Applies cyber-physical threat mutations to signals array.
        """
        pass


class ICircularBuffer(ABC):
    """Abstract Base Class for O(1) circular ring buffer semantics."""
    
    @abstractmethod
    def write(self, data: np.ndarray):
        """Writes data matrix (num_channels, step_samples) to circular buffer in O(1) time."""
        pass
        
    @abstractmethod
    def read_last(self, num_samples: int) -> np.ndarray:
        """Reads the most recent num_samples without copying the full buffer array."""
        pass
