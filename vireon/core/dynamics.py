import numpy as np
from typing import Any, Optional
from dataclasses import dataclass

@dataclass
class NeuralDynamicsConfig:
    beta_baseline: float = 10.0
    beta_entrained_max: float = 25.0
    beta_suppressed_min: float = 2.0
    beta_decay_rate: float = 0.05
    beta_forcing_rate: float = 0.1
    noise_std: float = 0.1
    forcing_scale: float = 5.0
class KuramotoModel:
    """
    Continuous Differential Equation Model of Neural Dynamics based on the Kuramoto model.
    Models a network of coupled neural oscillators to simulate entrainment, phase locking,
    and frequency following responses from deep brain stimulation (DBS) or external therapies.
    """
    def __init__(self, num_oscillators: int = 8, coupling_k: float = 2.0, seed: Optional[int] = None, config: Optional[NeuralDynamicsConfig] = None):
        self.config = config or NeuralDynamicsConfig()
        self.N = num_oscillators
        self.K = coupling_k
        self.rng = np.random.default_rng(seed)
        
        # Initialize phases randomly between 0 and 2*pi
        self.phases = self.rng.uniform(0, 2 * np.pi, self.N)
        
        # Natural frequencies (omega) in Hz.
        # We assign a mix of alpha (8-12Hz) and beta (13-30Hz) typical resting frequencies
        base_freqs_hz = self.rng.uniform(8.0, 25.0, self.N)
        self.omegas = 2.0 * np.pi * base_freqs_hz  # Convert to radians/sec
        
        # External forcing (from stimulation)
        self.forcing_amplitude = 0.0
        self.forcing_omega = 0.0
        
        # Derived metrics
        self.coherence = 0.0     # Order parameter R (0 to 1)
        self.beta_power = self.config.beta_baseline   # Simulated beta band power baseline
        
    def get_state(self) -> dict:
        return {
            "phases": self.phases.tolist(),
            "omegas": self.omegas.tolist(),
            "forcing_amplitude": self.forcing_amplitude,
            "forcing_omega": self.forcing_omega,
            "coherence": self.coherence,
            "beta_power": self.beta_power
        }

    def restore_state(self, state: dict):
        if "phases" in state:
            self.phases = np.array(state["phases"])
        if "omegas" in state:
            self.omegas = np.array(state["omegas"])
        self.forcing_amplitude = state.get("forcing_amplitude", self.forcing_amplitude)
        self.forcing_omega = state.get("forcing_omega", self.forcing_omega)
        self.coherence = state.get("coherence", self.coherence)
        self.beta_power = state.get("beta_power", self.beta_power)
        
    def set_forcing(self, amplitude_ma: float, frequency_hz: float):
        """
        Set external forcing from a simulated therapy device.
        """
        # Map mA amplitude to a forcing strength (arbitrary scaling for the ODE)
        self.forcing_amplitude = amplitude_ma * self.config.forcing_scale
        self.forcing_omega = 2.0 * np.pi * frequency_hz
        
    def tick(self, dt: float, global_time: float):
        """
        Step the ODE forward using the Euler method.
        """
        if dt <= 0:
            return
        def get_derivatives(phases, t):
            theta_diffs = phases[np.newaxis, :] - phases[:, np.newaxis]
            coupling = (self.K / self.N) * np.sum(np.sin(theta_diffs), axis=1)
            
            forcing: Any = 0.0
            if self.forcing_amplitude > 0:
                forcing = self.forcing_amplitude * np.sin(self.forcing_omega * t - phases)
                
            return self.omegas + coupling + forcing
            
        # Sub-stepping to maintain integration stability for high-frequency forcing
        max_freq = max(np.max(self.omegas), self.forcing_omega) / (2 * np.pi)
        if max_freq < 1.0:
            max_freq = 1.0
        
        # Stability criterion: dt_sub <= 1 / (10 * f_max)
        max_dt_sub = 1.0 / (10.0 * max_freq)
        
        num_steps = int(np.ceil(dt / max_dt_sub))
        dt_sub = dt / num_steps
        
        current_time = global_time
        
        for _ in range(num_steps):
            k1 = get_derivatives(self.phases, current_time)
            k2 = get_derivatives(self.phases + 0.5 * dt_sub * k1, current_time + 0.5 * dt_sub)
            k3 = get_derivatives(self.phases + 0.5 * dt_sub * k2, current_time + 0.5 * dt_sub)
            k4 = get_derivatives(self.phases + dt_sub * k3, current_time + dt_sub)
            
            dtheta = (dt_sub / 6.0) * (k1 + 2*k2 + 2*k3 + k4)
            
            # Add Wiener process (Brownian noise) for biological variance
            noise = self.rng.normal(0, self.config.noise_std, self.N) * np.sqrt(dt_sub)
            
            self.phases = self.phases + dtheta + noise
            self.phases = np.mod(self.phases, 2 * np.pi)
            current_time += dt_sub
            
        self._update_metrics()
        
    def _update_metrics(self):
        """
        Calculate macroscopic metrics from the oscillator phases.
        """
        # Kuramoto order parameter R: | (1/N) * sum(e^{i*theta}) |
        complex_phases = np.exp(1j * self.phases)
        order_param = np.abs(np.mean(complex_phases))
        self.coherence = float(order_param)
        
        # Simulate beta power changes. Entrainment at beta frequencies boosts it, 
        # while very high frequency (e.g. 130Hz DBS) typically suppresses beta power.
        if self.forcing_amplitude > 0:
            if 13.0 <= (self.forcing_omega / (2 * np.pi)) <= 30.0:
                self.beta_power += (self.config.beta_entrained_max * self.coherence - self.beta_power) * self.config.beta_forcing_rate
            elif (self.forcing_omega / (2 * np.pi)) > 100.0:
                # High freq suppression
                self.beta_power += (self.config.beta_suppressed_min - self.beta_power) * self.config.beta_forcing_rate
        else:
            # Drift back to baseline
            self.beta_power += (self.config.beta_baseline - self.beta_power) * self.config.beta_decay_rate
