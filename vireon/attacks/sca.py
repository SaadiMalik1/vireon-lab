"""
Side-Channel Attack (SCA) Emulator.

Simulates physical side-channel leakages (e.g., Differential Power Analysis)
from the Cortex-M stub. In medical implants, physical access might be achieved
post-explantation or via near-field EMF probes.
"""

import numpy as np
from typing import List, Tuple

class DPAEmulator:
    """
    Simulates Differential Power Analysis (DPA) traces using a Hamming Weight leakage model.
    When the Cortex-M stub processes cryptographic operations (like AES),
    it leaks power proportional to the number of set bits (Hamming weight) of the data being processed.
    """
    def __init__(self, noise_std_dev: float = 0.5, samples_per_byte: int = 10):
        self.noise_std_dev = noise_std_dev
        self.samples_per_byte = samples_per_byte

    def _hamming_weight(self, byte_val: int) -> int:
        """Calculates the Hamming weight (number of 1 bits) of a byte."""
        return bin(byte_val).count('1')

    def generate_power_trace(self, data: bytes) -> np.ndarray:
        """
        Generates a synthetic power trace for the given data buffer.
        :param data: The cryptographic key or payload being processed.
        :return: A 1D numpy array representing the power trace.
        """
        total_samples = len(data) * self.samples_per_byte
        trace = np.zeros(total_samples)

        for i, byte in enumerate(data):
            hw = self._hamming_weight(byte)
            # Power consumption is baseline + a factor * Hamming weight + Gaussian noise
            base_power = 10.0
            leakage = hw * 2.5
            
            start_idx = i * self.samples_per_byte
            end_idx = start_idx + self.samples_per_byte
            
            # Simulate the clock cycle profile for processing this byte
            # A simple shape: rising edge, steady, falling edge
            cycle_profile = np.sin(np.linspace(0, np.pi, self.samples_per_byte))
            
            noise = np.random.normal(0, self.noise_std_dev, self.samples_per_byte)
            
            trace[start_idx:end_idx] = (base_power + leakage) * cycle_profile + noise

        return trace

    def simulate_key_extraction(self, target_key: bytes, num_traces: int = 100) -> Tuple[bool, float]:
        """
        Simulates an attacker capturing multiple traces and running statistical DPA
        to extract the target key.
        Returns (success, confidence).
        """
        # In a real DPA, we correlate hypotheses against the traces.
        # Here we mock the success probability based on the noise level and number of traces.
        # Higher noise needs more traces.
        snr = 2.5 / (self.noise_std_dev + 1e-9)
        # Approximate probability of extraction success
        extraction_power = min(1.0, (snr * np.sqrt(num_traces)) / 50.0)
        
        success = extraction_power > 0.8
        confidence = extraction_power
        
        return success, confidence
