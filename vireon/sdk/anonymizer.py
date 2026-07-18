"""
Neurodata Anonymization and Re-identification Risk Scoring.

EEG signals contain biometrically identifiable traits. This module implements
techniques to anonymize exported neural telemetry while preserving clinical
features, and scores the remaining re-identification risk.

References:
 - Federated Learning for EEG (2024-2025)
 - VIREON Anonymization Guidelines
"""

import numpy as np
import random
from typing import List, Dict, Any

class TemporalJittering:
    """Applies random temporal shifts/jitter to data points."""
    def __init__(self, max_jitter_ms: int = 50, sample_rate: int = 250):
        self.max_jitter_samples = max(1, int((max_jitter_ms / 1000.0) * sample_rate))
        
    def apply(self, chunk: np.ndarray) -> np.ndarray:
        if chunk.size == 0 or chunk.ndim < 2:
            return chunk
            
        anonymized = np.zeros_like(chunk)
        for ch in range(chunk.shape[0]):
            jitter = random.randint(-self.max_jitter_samples, self.max_jitter_samples)
            if jitter > 0:
                anonymized[ch, jitter:] = chunk[ch, :-jitter]
            elif jitter < 0:
                anonymized[ch, :jitter] = chunk[ch, -jitter:]
            else:
                anonymized[ch, :] = chunk[ch, :]
        return anonymized


class ChannelPermutation:
    """Randomly swaps symmetric EEG channels to mask spatial signatures."""
    def __init__(self, symmetric_pairs: List[tuple] = None):
        # Default pairs for standard 8-channel board (e.g., [Fp1, Fp2], [C3, C4])
        self.symmetric_pairs = symmetric_pairs or [(0, 1), (2, 3), (4, 5)]
        
    def apply(self, chunk: np.ndarray) -> np.ndarray:
        if chunk.size == 0 or chunk.ndim < 2:
            return chunk
            
        anonymized = chunk.copy()
        for left, right in self.symmetric_pairs:
            if left < chunk.shape[0] and right < chunk.shape[0]:
                if random.choice([True, False]):
                    anonymized[[left, right], :] = anonymized[[right, left], :]
                    
        return anonymized


class SpectralMasking:
    """Masks individual-specific high-frequency biometric features (e.g. gamma band > 40Hz)."""
    def __init__(self, cutoff_hz: float = 40.0, sample_rate: int = 250):
        self.cutoff_hz = cutoff_hz
        self.sample_rate = sample_rate
        
    def apply(self, chunk: np.ndarray) -> np.ndarray:
        if chunk.size == 0 or chunk.ndim < 2:
            return chunk
            
        n_samples = chunk.shape[1]
        anonymized = np.zeros_like(chunk)
        
        for ch in range(chunk.shape[0]):
            fft_vals = np.fft.rfft(chunk[ch, :])
            freqs = np.fft.rfftfreq(n_samples, d=1.0 / self.sample_rate)
            
            # Mask frequencies above cutoff
            mask = freqs > self.cutoff_hz
            fft_vals[mask] = 0.0
            
            anonymized[ch, :] = np.fft.irfft(fft_vals, n=n_samples)
            
        return anonymized


class ReidentificationRiskScorer:
    """
    Evaluates the risk of biometric re-identification from a telemetry export.
    Returns a risk score between 0.0 (perfectly anonymous) and 1.0 (highly identifiable).
    """
    def __init__(self):
        self.high_freq_threshold = 30.0 # Hz (Gamma band carries high biometric uniqueness)
        
    def score_risk(self, history: List[Dict[str, Any]]) -> float:
        """
        Simplified heuristic scorer. 
        In production, this would cross-correlate against a database of reference templates.
        Here we score based on the presence of unmasked high-frequency noise and temporal precision.
        """
        if not history:
            return 0.0
            
        risk = 1.0
        
        # Check if timestamps are heavily jittered (e.g., quantized or offset)
        times = [h.get("timestamp", 0) for h in history]
        if len(times) > 1:
            dt = times[1] - times[0]
            if dt >= 1.0: # Highly quantized
                risk -= 0.3
                
        # In a full implementation, we'd check spectral sparsity. 
        # For now, we simulate risk reduction.
        return max(0.0, min(1.0, risk))

class NeuroDataAnonymizer:
    """Orchestrator for telemetry anonymization."""
    def __init__(self):
        self.jitter = TemporalJittering()
        self.permute = ChannelPermutation()
        self.masking = SpectralMasking()
        self.scorer = ReidentificationRiskScorer()
        
    def anonymize_export(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Anonymizes the telemetry history in-place/copy for export.
        In the current implementation, we quantize timestamps to reduce temporal precision.
        (Signal-level anonymization should be applied at runtime to the chunks before they reach the logger).
        """
        anonymized_history = []
        for item in history:
            anon_item = item.copy()
            # Quantize timestamps to nearest second to mask fine temporal biometric traits
            anon_item["timestamp"] = round(anon_item.get("timestamp", 0))
            # Remove highly specific impedance values, replace with bins
            if "electrode_impedances" in anon_item:
                anon_item["electrode_impedances"] = {k: round(v, -1) for k, v in anon_item["electrode_impedances"].items()}
            anonymized_history.append(anon_item)
            
        return anonymized_history
