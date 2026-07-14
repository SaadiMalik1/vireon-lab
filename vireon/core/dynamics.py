import numpy as np
from typing import Any
class KuramotoModel:
    """
    Continuous Differential Equation Model of Neural Dynamics based on the Kuramoto model.
    Models a network of coupled neural oscillators to simulate entrainment, phase locking,
    and frequency following responses from deep brain stimulation (DBS) or external therapies.
    """
    def __init__(self, num_oscillators: int = 8, coupling_k: float = 2.0):
        self.N = num_oscillators
        self.K = coupling_k
        
        # Initialize phases randomly between 0 and 2*pi
        self.phases = np.random.uniform(0, 2 * np.pi, self.N)
        
        # Natural frequencies (omega) in Hz.
        # We assign a mix of alpha (8-12Hz) and beta (13-30Hz) typical resting frequencies
        base_freqs_hz = np.random.uniform(8.0, 25.0, self.N)
        self.omegas = 2.0 * np.pi * base_freqs_hz  # Convert to radians/sec
        
        # External forcing (from stimulation)
        self.forcing_amplitude = 0.0
        self.forcing_omega = 0.0
        
        # Derived metrics
        self.coherence = 0.0     # Order parameter R (0 to 1)
        self.beta_power = 10.0   # Simulated beta band power baseline
        
    def set_forcing(self, amplitude_ma: float, frequency_hz: float):
        """
        Set external forcing from a simulated therapy device.
        """
        # Map mA amplitude to a forcing strength (arbitrary scaling for the ODE)
        self.forcing_amplitude = amplitude_ma * 5.0
        self.forcing_omega = 2.0 * np.pi * frequency_hz
        
    def tick(self, dt: float, global_time: float):
        """
        Step the ODE forward using the Euler method.
        """
        if dt <= 0:
            return
            
        # Calculate coupling term: (K/N) * sum_j sin(theta_j - theta_i)
        # Using broadcasting to compute all pairs
        theta_diffs = self.phases[np.newaxis, :] - self.phases[:, np.newaxis]
        coupling = (self.K / self.N) * np.sum(np.sin(theta_diffs), axis=1)
        
        # Calculate external forcing term: F * sin(Omega * t - theta_i)
        forcing: Any = 0.0
        if self.forcing_amplitude > 0:
            forcing = self.forcing_amplitude * np.sin(self.forcing_omega * global_time - self.phases)
            
        # Full Kuramoto equation: d(theta)/dt = omega + coupling + forcing
        dtheta_dt = self.omegas + coupling + forcing
        
        # Euler integration step
        self.phases = self.phases + dtheta_dt * dt
        
        # Keep phases in [0, 2*pi)
        self.phases = np.mod(self.phases, 2 * np.pi)
        
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
                self.beta_power += (25.0 * self.coherence - self.beta_power) * 0.1
            elif (self.forcing_omega / (2 * np.pi)) > 100.0:
                # High freq suppression
                self.beta_power += (2.0 - self.beta_power) * 0.1
        else:
            # Drift back to baseline (around 10)
            self.beta_power += (10.0 - self.beta_power) * 0.05
