import numpy as np
from vireon.core.twin import DigitalTwin
from vireon.core.security import NeuroSignalAssuranceEngine

def test_autoencoder_and_cusum():
    twin = DigitalTwin()
    ids = NeuroSignalAssuranceEngine(twin)
    
    # Send nominal data (pink noise-like) to establish baseline
    for _ in range(50):
        data = np.random.normal(0, 1.0, (8, 250))
        anomalies = ids.analyze_signal(data)
        assert "SLOW_DRIFT_ANOMALY" not in anomalies
        
    # Introduce slow drift
    for i in range(15):
        data = np.random.normal(i * 1.5, 1.0, (8, 250))
        anomalies = ids.analyze_signal(data)
        if "SLOW_DRIFT_ANOMALY" in anomalies:
            break
            
    assert "SLOW_DRIFT_ANOMALY" in anomalies
    
    # Test Autoencoder structural deviation
    # We send data with completely different covariance structure
    abnormal_data = np.random.normal(0, 100.0, (8, 250))
    # Inject anti-correlation to break learned PCA structure
    abnormal_data[1, :] = -abnormal_data[0, :] * 50.0
    
    anomalies = ids.analyze_signal(abnormal_data)
    if "STRUCTURAL_DEVIATION_ANOMALY" not in anomalies:
        # Give it another push
        anomalies = ids.analyze_signal(abnormal_data * 10)
        
    assert "STRUCTURAL_DEVIATION_ANOMALY" in anomalies
