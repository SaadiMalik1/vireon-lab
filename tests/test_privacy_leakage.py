import numpy as np
from vireon.core.privacy_leakage import P300Analyzer

def test_p300_analyzer_init():
    analyzer = P300Analyzer(sample_rate=250, threshold_uv=15.0)
    assert analyzer.sample_rate == 250
    assert analyzer.threshold_uv == 15.0
    assert analyzer.window_size == 150

def test_scan_empty_signal():
    analyzer = P300Analyzer()
    result = analyzer.scan_for_leakage(np.array([]))
    assert result["leakage_detected"] is False
    assert result["p300_events_detected"] == 0

def test_scan_with_event_markers():
    analyzer = P300Analyzer(sample_rate=100, threshold_uv=10.0)
    
    # 2 channels, 2 seconds
    signal = np.zeros((2, 200))
    
    # Inject a P300 peak after marker at 0.5s
    # Peak should be between 250ms and 500ms post-stimulus
    # So between 0.75s and 1.0s. Let's put a peak at 0.8s (idx 80)
    signal[:, 75:90] = 12.0 # Greater than threshold 10.0
    
    markers = [0.5, 1.5] # 1.5 won't have a peak
    
    result = analyzer.scan_for_leakage(signal, event_markers=markers)
    
    assert result["leakage_detected"] is True
    assert result["p300_events_detected"] == 1
    assert result["max_p300_amplitude_uv"] >= 12.0
    assert result["risk_level"] == "MEDIUM"

def test_scan_with_event_markers_out_of_bounds():
    analyzer = P300Analyzer(sample_rate=100, threshold_uv=10.0)
    signal = np.zeros((2, 100)) # 1 second
    
    markers = [0.9] # Window will be out of bounds (0.9 + 0.5 = 1.4s)
    
    result = analyzer.scan_for_leakage(signal, event_markers=markers)
    assert result["leakage_detected"] is False

def test_scan_blind():
    analyzer = P300Analyzer(sample_rate=100, threshold_uv=10.0)
    
    signal = np.zeros((2, 300))
    # Inject a peak that will survive the moving average (window=10)
    signal[0, 100:120] = 15.0
    
    result = analyzer.scan_for_leakage(signal)
    
    assert result["leakage_detected"] is True
    assert result["p300_events_detected"] > 0
    assert result["max_p300_amplitude_uv"] >= 14.0

def test_scan_blind_high_risk():
    analyzer = P300Analyzer(sample_rate=100, threshold_uv=10.0)
    # analyzer.window_size is 60 (0.6 * 100)
    # So to get > 3 events, we need signal length to be at least 4 * 60 = 240
    signal = np.zeros((2, 400))
    
    # Inject multiple peaks
    signal[0, 50:60] = 15.0
    signal[0, 150:160] = 15.0
    signal[0, 250:260] = 15.0
    signal[0, 350:360] = 15.0
    
    result = analyzer.scan_for_leakage(signal)
    
    assert result["leakage_detected"] is True
    assert result["p300_events_detected"] >= 4
    assert result["risk_level"] == "HIGH"
