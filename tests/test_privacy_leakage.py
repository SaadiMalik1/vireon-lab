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
from vireon.runtime.privacy_leakage import P300Analyzer

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
    # Inject a wide peak (width 20) that will survive the moving average (window=10)
    # and have a strict unique peak
    peak = np.sin(np.linspace(0, np.pi, 20)) * 25.0
    signal[0, 100:120] = peak
    
    result = analyzer.scan_for_leakage(signal)
    
    assert result["leakage_detected"] is True
    assert result["p300_events_detected"] > 0
    assert result["max_p300_amplitude_uv"] >= 14.0

def test_scan_blind_high_risk():
    analyzer = P300Analyzer(sample_rate=100, threshold_uv=10.0)
    # analyzer.window_size is 60 (0.6 * 100)
    # So to get > 3 events, we need signal length to be at least 4 * 60 = 240
    signal = np.zeros((2, 400))
    
    # Inject multiple sharp peaks
    peak = np.sin(np.linspace(0, np.pi, 20)) * 25.0
    signal[0, 50:70] = peak
    signal[0, 150:170] = peak
    signal[0, 250:270] = peak
    signal[0, 350:370] = peak
    
    result = analyzer.scan_for_leakage(signal)
    
    assert result["leakage_detected"] is True
    assert result["p300_events_detected"] >= 4
    assert result["risk_level"] == "HIGH"
