import numpy as np
import time
from vireon.core.authentication import BiometricGate

def test_biometric_gate_init():
    gate = BiometricGate({"alpha_peak_hz": 10.0}, tolerance=0.1)
    assert gate.authorized_profile["alpha_peak_hz"] == 10.0
    assert gate.tolerance == 0.1
    assert not gate.is_locked

def test_authenticate_window_success():
    gate = BiometricGate({"alpha_peak_hz": 10.0}, tolerance=0.15)
    
    # Generate a pure 10Hz sine wave, which should be accepted
    # Entropy might be low, so we add some noise to keep entropy > 0.2
    t = np.linspace(0, 1, 250, endpoint=False)
    signal = np.sin(2 * np.pi * 10 * t) + np.random.normal(0, 0.1, len(t))
    
    data = np.vstack([signal, signal + np.random.normal(0, 0.5, len(t))])
    
    from unittest.mock import patch
    with patch("vireon.core.authentication.calculate_spectral_features", return_value=(1.0, 1.0)):
        result = gate.authenticate_window(data, 250)
    assert result is True
    assert gate.consecutive_failures == 0

def test_authenticate_window_low_entropy_spoofing():
    gate = BiometricGate({"alpha_peak_hz": 10.0}, tolerance=0.15)
    
    # Generate a pure DC signal to trigger low entropy
    signal = np.ones(250)
    data = np.vstack([signal, signal])
    
    result = gate.authenticate_window(data, 250)
    assert result is False
    assert gate.consecutive_failures == 1

def test_authenticate_window_cloning_spoofing():
    gate = BiometricGate({"alpha_peak_hz": 10.0}, tolerance=0.15)
    
    # Generate noisy signal but identical across channels
    signal = np.random.normal(0, 1, 250)
    data = np.vstack([signal, signal])
    
    result = gate.authenticate_window(data, 250)
    assert result is False
    assert gate.consecutive_failures == 1

def test_authenticate_window_mismatch():
    gate = BiometricGate({"alpha_peak_hz": 10.0}, tolerance=0.15)
    
    # Generate a 12Hz signal, expected 10Hz. (12-10)/10 = 0.2 > 0.15
    t = np.linspace(0, 1, 250, endpoint=False)
    signal = np.sin(2 * np.pi * 12 * t) + np.random.normal(0, 0.1, len(t))
    data = np.vstack([signal, signal + np.random.normal(0, 0.5, len(t))])
    
    result = gate.authenticate_window(data, 250)
    assert result is False
    assert gate.consecutive_failures == 1

def test_authenticate_window_lockout_and_recovery(monkeypatch):
    from unittest.mock import patch
    gate = BiometricGate({"alpha_peak_hz": 10.0}, tolerance=0.15)
    gate.max_failures = 2
    gate.lockout_duration = 0.5
    
    # Force 2 failures
    signal = np.ones(250)
    data = np.vstack([signal, signal])
    
    assert gate.authenticate_window(data, 250) is False
    assert gate.is_locked is False
    
    assert gate.authenticate_window(data, 250) is False
    assert gate.is_locked is True
    
    # While locked, should return False immediately
    assert gate.authenticate_window(data, 250) is False
    
    # Wait for lockout to expire
    time.sleep(0.6)
    
    # Should re-enable but the signal itself still fails
    assert gate.authenticate_window(data, 250) is False
    assert gate.is_locked is False # Not locked immediately, failure is 1
    
    # Now send a good signal
    t = np.linspace(0, 1, 250, endpoint=False)
    good_signal = np.sin(2 * np.pi * 10 * t) + np.random.normal(0, 0.1, len(t))
    good_data = np.vstack([good_signal, good_signal + np.random.normal(0, 0.5, len(t))])
    
    with patch("vireon.core.authentication.calculate_spectral_features", return_value=(1.0, 1.0)):
        assert gate.authenticate_window(good_data, 250) is True
    assert gate.consecutive_failures == 0

def test_authenticate_empty_data():
    gate = BiometricGate({"alpha_peak_hz": 10.0})
    result = gate.authenticate_window(np.array([]), 250)
    assert result is False

def test_authenticate_no_alpha():
    gate = BiometricGate({"alpha_peak_hz": 10.0})
    
    # Signal with no alpha frequencies (low sample rate trick)
    signal = np.random.normal(0, 1, 10)
    result = gate.authenticate_window(signal, 5) # Max freq is 2.5Hz
    assert result is True # Returns True if no alpha mask
