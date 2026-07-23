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

import numpy as np
from vireon_lab.engine.interfaces import ISignalGenerator

class JansenRitNeuralMassGenerator(ISignalGenerator):
    """
    Biologically plausible Jansen-Rit cortical neural mass differential model.
    Models interaction between pyramidal neurons, excitatory interneurons, and inhibitory interneurons.
    Generates non-sinusoidal alpha/beta oscillations with realistic non-linear sigmoid activation.
    """
    def __init__(self, num_channels: int = 8, C: float = 135.0, A: float = 3.25, B: float = 22.0, a: float = 100.0, b: float = 50.0):
        self.num_channels = num_channels
        self.C = C
        self.A = A  # Excitatory gain (mV)
        self.B = B  # Inhibitory gain (mV)
        self.a = a  # Excitatory time constant (s^-1)
        self.b = b  # Inhibitory time constant (s^-1)
        
        # State vector per channel: [y0, y1, y2, y3, y4, y5]
        self.state = np.zeros((num_channels, 6))
        self.v0 = 6.0    # Sigmoid threshold (mV)
        self.e0 = 2.5    # Max firing rate (s^-1)
        self.r = 0.56    # Sigmoid slope (mV^-1)

    def _sigmoid(self, v: np.ndarray) -> np.ndarray:
        return (2.0 * self.e0) / (1.0 + np.exp(self.r * (self.v0 - v)))

    def generate(self, num_samples: int, t_start: float, sampling_rate: float, rng: np.random.Generator) -> np.ndarray:
        dt = 1.0 / sampling_rate
        signals = np.zeros((self.num_channels, num_samples))
        
        for ch in range(self.num_channels):
            y0, y1, y2, y3, y4, y5 = self.state[ch, :]
            
            for i in range(num_samples):
                # Input Gaussian noise to pyramidal population
                p_in = rng.normal(220.0, 30.0)
                
                # Membrane potential difference
                v_pyr = y1 - y2
                
                # Sigmoidal transformation into firing rates
                S_pyr = self._sigmoid(v_pyr)
                S_exc = self._sigmoid(C1 * S_pyr) if 'C1' in locals() else self._sigmoid(self.C * 0.8 * S_pyr)
                S_inh = self._sigmoid(C3 * S_pyr) if 'C3' in locals() else self._sigmoid(self.C * 0.25 * S_pyr)
                
                # Differential equations step (Euler-Maruyama integration)
                dy0 = y3
                dy3 = self.A * self.a * S_pyr - 2.0 * self.a * y3 - (self.a ** 2) * y0
                
                dy1 = y4
                dy4 = self.A * self.a * (p_in + self.C * 0.8 * S_exc) - 2.0 * self.a * y4 - (self.a ** 2) * y1
                
                dy2 = y5
                dy5 = self.B * self.b * (self.C * 0.25 * S_inh) - 2.0 * self.b * y5 - (self.b ** 2) * y2
                
                y0 += dy0 * dt
                y3 += dy3 * dt
                y1 += dy1 * dt
                y4 += dy4 * dt
                y2 += dy2 * dt
                y5 += dy5 * dt
                
                signals[ch, i] = v_pyr * 10.0 # Scale to microvolts (uV)
                
            self.state[ch, :] = [y0, y1, y2, y3, y4, y5]
            
        return signals


class ColoredNoiseARGenerator(ISignalGenerator):
    """
    Multivariate Auto-Regressive (AR) colored pink/red noise process generator.
    Simulates realistic scale-free 1/f background neural noise.
    """
    def __init__(self, num_channels: int = 8, alpha: float = 0.85):
        self.num_channels = num_channels
        self.alpha = alpha
        self.prev_state = np.zeros((num_channels, 1))

    def generate(self, num_samples: int, t_start: float, sampling_rate: float, rng: np.random.Generator) -> np.ndarray:
        signals = np.zeros((self.num_channels, num_samples))
        for ch in range(self.num_channels):
            white_noise = rng.normal(0, 10.0, size=num_samples)
            current_val = self.prev_state[ch, 0]
            for i in range(num_samples):
                current_val = self.alpha * current_val + (1 - self.alpha) * white_noise[i]
                signals[ch, i] = current_val
            self.prev_state[ch, 0] = current_val
        return signals
