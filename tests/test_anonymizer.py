import numpy as np
from vireon.core.anonymizer import (
    TemporalJittering,
    ChannelPermutation,
    SpectralMasking,
    ReidentificationRiskScorer
)

def test_temporal_jittering():
    jitter = TemporalJittering(max_jitter_ms=50, sample_rate=250)
    chunk = np.ones((2, 100))
    anonymized = jitter.apply(chunk)
    assert anonymized.shape == chunk.shape
    
    # Test empty
    empty_chunk = np.array([])
    assert jitter.apply(empty_chunk).size == 0

def test_channel_permutation():
    perm = ChannelPermutation(symmetric_pairs=[(0, 1)])
    chunk = np.vstack([np.ones(10), np.zeros(10)])
    
    # Since random, we just run it and check shape
    anonymized = perm.apply(chunk)
    assert anonymized.shape == chunk.shape
    
    # Test empty
    assert perm.apply(np.array([])).size == 0

def test_spectral_masking():
    mask = SpectralMasking(cutoff_hz=40.0, sample_rate=250)
    
    # Create a signal with low and high frequency
    t = np.linspace(0, 1, 250, endpoint=False)
    # 10 Hz (kept) + 50 Hz (masked)
    signal = np.sin(2 * np.pi * 10 * t) + np.sin(2 * np.pi * 50 * t)
    chunk = np.vstack([signal, signal])
    
    anonymized = mask.apply(chunk)
    assert anonymized.shape == chunk.shape
    
    # Test empty
    assert mask.apply(np.array([])).size == 0

def test_risk_scorer():
    scorer = ReidentificationRiskScorer()
    assert scorer.score_risk([]) == 0.0
    
    history = [
        {"signal_chunk": np.ones((2, 250)).tolist(), "sample_rate": 250},
        {"signal_chunk": np.ones((2, 250)).tolist(), "sample_rate": 250}
    ]
    
    risk = scorer.score_risk(history)
    assert 0.0 <= risk <= 1.0
