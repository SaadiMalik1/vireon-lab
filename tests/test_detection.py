import numpy as np
from vireon.core.twin import DigitalTwin
from vireon.core.detection import (
    calculate_spectral_features,
    LinearAutoencoderIDS,
    SecurityEngine,
    CoherenceEngine,
    TORCH_AVAILABLE
)

def test_calculate_spectral_features():
    signal = np.sin(2 * np.pi * 10 * np.linspace(0, 1, 250))
    entropy, crest = calculate_spectral_features(signal)
    assert isinstance(entropy, float)
    assert isinstance(crest, float)

def test_linear_autoencoder_ids():
    ids = LinearAutoencoderIDS(n_components=2)
    data = np.random.randn(8, 100)
    
    # Should buffer and return 0
    err = ids.detect(data)
    assert err == 0.0
    
    # Force calibration by feeding 100 times
    for _ in range(105):
        err = ids.detect(data)
    
    assert ids.is_fitted is True
    assert err >= 0.0

def test_coherence_engine():
    engine = CoherenceEngine()
    
    # Not stimulating
    score = engine.evaluate(False, 4.0)
    assert score > 0
    
    # Stimulating but body not reacting
    for _ in range(15):
        score = engine.evaluate(True, 4.0)
    assert score < 1.0

def test_security_engine_score_signal():
    twin = DigitalTwin(num_channels=8)
    engine = SecurityEngine(twin)
    
    data = np.random.randn(8, 10)
    score = engine.score_signal(data)
    assert score >= 0.0
    
    # Test NaN
    nan_data = np.full((8, 10), np.nan)
    assert engine.score_signal(nan_data) == float('inf')

def test_security_engine_analyze_commands():
    twin = DigitalTwin(num_channels=8)
    engine = SecurityEngine(twin)
    
    anomalies = engine.analyze_commands(1.0, 130.0)
    assert len(anomalies) == 0
    
    # High frequency changes
    for _ in range(6):
        twin._sim_clock += 0.1
        anomalies = engine.analyze_commands(np.random.rand(), 130.0)
        
    assert "HIGH_FREQUENCY_COMMAND_ANOMALY" in anomalies

def test_security_engine_slow_drift():
    twin = DigitalTwin(num_channels=8)
    engine = SecurityEngine(twin)
    engine.dynamic_baseline_enabled = True
    
    # Initialize baseline
    engine.analyze_signal(np.zeros((8, 100)))
    
    # Inject slow drift
    drift_data = np.ones((8, 100)) * 5.0
    for _ in range(10):
        anomalies = engine.analyze_signal(drift_data)
        if "SLOW_DRIFT_ANOMALY" in anomalies:
            break
            
def test_spectral_spoofing():
    twin = DigitalTwin(num_channels=8)
    engine = SecurityEngine(twin)
    
    # Pure tone signal (high spectral crest factor, low spectral entropy)
    t = np.linspace(0, 1, 100)
    data = np.zeros((8, 100))
    for i in range(8):
        data[i, :] = 1000.0 * np.sin(2 * np.pi * 50 * t)
    
    anomalies = engine.analyze_signal(data)
    assert "SPECTRAL_SPOOFING_ANOMALY" in anomalies

if TORCH_AVAILABLE:
    from vireon.core.detection import DeepAutoencoderIDS
    
    def test_deep_autoencoder_ids():
        ids = DeepAutoencoderIDS(input_dim=8)
        data = np.random.randn(8, 100)
        
        # Buffer
        err = ids.detect(data)
        assert err == 0.0
        
        # Force calibration
        for _ in range(55):
            err = ids.detect(data)
        
        assert ids.is_fitted is True
        assert err >= 0.0
