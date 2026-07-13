"""
Differential Privacy and Anonymization Engine for NeuroShield.

This module implements (ε, δ)-Differential Privacy mechanisms tailored
for neural telemetry, adding calibrated Laplacian noise to mask biometrically
identifiable traits while preserving macroscopic population dynamics.

Reference: Adversarial Attacks and Defenses on EEG-based BCIs (2024-2025).
"""

import numpy as np

class PrivacyBudgetTracker:
    """Tracks the total privacy budget consumed over a session."""
    def __init__(self, max_epsilon: float = 10.0):
        self.max_epsilon = max_epsilon
        self.consumed_epsilon = 0.0

    def consume(self, epsilon: float) -> bool:
        """Consume budget. Returns False if budget exceeded."""
        if self.consumed_epsilon + epsilon > self.max_epsilon:
            return False
        self.consumed_epsilon += epsilon
        return True

    def get_remaining(self) -> float:
        return max(0.0, self.max_epsilon - self.consumed_epsilon)


class DifferentialPrivacyFilter:
    """
    Applies Differential Privacy to streaming EEG chunks.
    
    Uses the Laplace mechanism to inject calibrated noise.
    The sensitivity is based on the maximum expected amplitude variation
    in microvolts (e.g., 100 µV for standard EEG).
    """
    def __init__(self, epsilon: float = 1.0, sensitivity_uv: float = 100.0, seed: int = None):
        self.epsilon = epsilon
        self.sensitivity = sensitivity_uv
        # scale parameter b = sensitivity / epsilon
        self.scale = self.sensitivity / self.epsilon if self.epsilon > 0 else 0.0
        self.rng = np.random.default_rng(seed)
        
    def filter_signal(self, chunk: np.ndarray) -> np.ndarray:
        """
        Add Laplacian noise to the signal to provide differential privacy.
        """
        if chunk.size == 0 or self.epsilon <= 0:
            return chunk

        # Draw noise from Laplace distribution: Laplace(loc=0, scale=b)
        noise = self.rng.laplace(loc=0.0, scale=self.scale, size=chunk.shape)
        
        return chunk + noise
