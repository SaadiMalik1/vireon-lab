"""
Neuro-Biometric Authentication Gate.

Simulates continuous or one-time authentication based on unique neural signatures
(e.g., individual alpha frequency or ERP characteristics). If the signature deviates
from the authorized user profile, data egress or device control is locked down to
prevent physical spoofing or "borrowed" implant usage.
"""

import numpy as np
from typing import Dict

class BiometricGate:
    def __init__(self, authorized_profile: Dict[str, float], tolerance: float = 0.15):
        """
        :param authorized_profile: Expected baseline features (e.g., {'alpha_peak_hz': 10.5}).
        :param tolerance: Allowed deviation margin before lockdown.
        """
        self.authorized_profile = authorized_profile
        self.tolerance = tolerance
        self.is_locked = False
        self.consecutive_failures = 0
        self.max_failures = 5

    def authenticate_window(self, data: np.ndarray, sample_rate: int) -> bool:
        """
        Analyzes a signal window to extract the user's alpha peak and compares
        it to the authorized profile.
        Returns True if authenticated, False otherwise.
        """
        if self.is_locked:
            return False
            
        # Extract features (mock implementation for simulation)
        # We simulate a simple FFT-based alpha peak detection.
        if len(data.shape) > 1:
            # use channel 0 for biometric auth
            signal = data[0, :]
        else:
            signal = data
            
        n = len(signal)
        if n == 0:
            return True
            
        fft_vals = np.abs(np.fft.rfft(signal))
        freqs = np.fft.rfftfreq(n, d=1.0/sample_rate)
        
        # Look for peak in alpha band (8-13 Hz)
        alpha_mask = (freqs >= 8.0) & (freqs <= 13.0)
        
        if not np.any(alpha_mask):
            return True
            
        alpha_fft = fft_vals[alpha_mask]
        alpha_freqs = freqs[alpha_mask]
        
        peak_idx = np.argmax(alpha_fft)
        observed_peak = alpha_freqs[peak_idx]
        
        expected_peak = self.authorized_profile.get("alpha_peak_hz", 10.0)
        
        # Check tolerance
        deviation = abs(observed_peak - expected_peak) / expected_peak
        
        if deviation > self.tolerance:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.max_failures:
                self.is_locked = True
                print(f"[BiometricGate] ALERT: Biometric mismatch! Locking device. Observed: {observed_peak:.1f}Hz, Expected: {expected_peak:.1f}Hz")
            return False
        else:
            # Recover
            self.consecutive_failures = max(0, self.consecutive_failures - 1)
            return True
