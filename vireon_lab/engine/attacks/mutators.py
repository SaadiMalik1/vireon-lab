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
from vireon_lab.engine.interfaces import IAttackMutator

class GaussianNoiseAttack(IAttackMutator):
    """Injects high-variance Gaussian white/pink noise perturbation."""
    def mutate(self, signals: np.ndarray, t_axis: np.ndarray, intensity: float, rng: np.random.Generator) -> np.ndarray:
        noise_level = 35.0 * intensity
        return signals + rng.normal(0, noise_level, size=signals.shape)


class DCOffsetDriftAttack(IAttackMutator):
    """Simulates linear electrode DC offset amplifier baseline drift."""
    def mutate(self, signals: np.ndarray, t_axis: np.ndarray, intensity: float, rng: np.random.Generator) -> np.ndarray:
        out = signals.copy()
        drift = (t_axis - t_axis[0]) * 20.0 * intensity
        for ch in range(signals.shape[0]):
            out[ch, :] += drift
        return out


class DoSGroundingAttack(IAttackMutator):
    """Denial of Service (DoS) - grounds selected sensor channels (0 uV output)."""
    def mutate(self, signals: np.ndarray, t_axis: np.ndarray, intensity: float, rng: np.random.Generator) -> np.ndarray:
        out = signals.copy()
        for ch in range(0, min(4, signals.shape[0])):
            out[ch, :] = rng.normal(0, 0.05, size=signals.shape[1])
        return out


class SessionReplayAttack(IAttackMutator):
    """Injects recorded periodic high-amplitude replay trace."""
    def mutate(self, signals: np.ndarray, t_axis: np.ndarray, intensity: float, rng: np.random.Generator) -> np.ndarray:
        out = signals.copy()
        replay_pattern = 60.0 * np.sin(2 * np.pi * 15.0 * t_axis) * intensity
        out[0, :] = replay_pattern
        out[1, :] = replay_pattern
        return out


class DBSPulseOverrideAttack(IAttackMutator):
    """Injects high-frequency 130 Hz stimulation override pulses into motor channels."""
    def mutate(self, signals: np.ndarray, t_axis: np.ndarray, intensity: float, rng: np.random.Generator) -> np.ndarray:
        out = signals.copy()
        dbs_pulse = 80.0 * np.sign(np.sin(2 * np.pi * 130.0 * t_axis)) * intensity
        out[2, :] += dbs_pulse
        out[3, :] += dbs_pulse
        return out
