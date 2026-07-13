"""
EEG Data Leakage Analyzer (P300 Speller / ERP Leakage).

Analyzes raw EEG telemetry for involuntary Event-Related Potentials (ERPs),
specifically the P300 wave. The P300 is a positive deflection occurring ~300ms
after a recognized stimulus. If leaked, this can be exploited for neuro-phishing
(e.g., extracting passwords, PINs, or subconscious preferences).
"""

import numpy as np
from typing import Dict, Any, List

class P300Analyzer:
    def __init__(self, sample_rate: int = 250, threshold_uv: float = 15.0):
        """
        Initializes the P300 leakage analyzer.
        :param sample_rate: EEG sampling rate in Hz.
        :param threshold_uv: Amplitude threshold (uV) indicating a strong P300 response.
        """
        self.sample_rate = sample_rate
        self.threshold_uv = threshold_uv
        # P300 typically peaks between 250ms and 500ms post-stimulus.
        # We will look for prominent slow positive waves.
        self.window_size = int(0.6 * sample_rate)  # 600ms window

    def scan_for_leakage(self, signal: np.ndarray, event_markers: List[float] = None) -> Dict[str, Any]:
        """
        Scans an EEG signal block (channels, samples) for P300 leakage.
        If event_markers (timestamps in seconds) are provided, it specifically
        checks the 250-500ms window post-event.
        Otherwise, it does a blind morphological search for P300-like peaks.
        """
        if signal.size == 0 or signal.ndim < 2:
            return {"leakage_detected": False, "risk_level": "LOW", "p300_events": 0}

        n_channels, n_samples = signal.shape
        p300_events = 0
        max_peak = 0.0

        if event_markers:
            # Event-locked ERP analysis
            for marker in event_markers:
                # Convert marker (sec) to sample index
                idx = int(marker * self.sample_rate)
                start_window = idx + int(0.25 * self.sample_rate) # 250ms
                end_window = idx + int(0.50 * self.sample_rate)   # 500ms
                
                if end_window > n_samples:
                    continue
                    
                # A P300 is typically most prominent on midline electrodes (Cz, Pz)
                # We'll average across all channels for a robust estimate in this mock
                mean_signal = np.mean(signal[:, start_window:end_window], axis=0)
                peak_amplitude = np.max(mean_signal)
                
                if peak_amplitude > max_peak:
                    max_peak = peak_amplitude
                    
                if peak_amplitude > self.threshold_uv:
                    p300_events += 1
        else:
            # Blind scanning (Sliding window)
            # Apply a simple low-pass filter (moving average) to isolate the slow P300 wave (approx 1-10Hz)
            window = int(0.1 * self.sample_rate) # 100ms moving average
            if window < 1: window = 1
            
            for ch in range(n_channels):
                # Simple moving average
                smoothed = np.convolve(signal[ch, :], np.ones(window)/window, mode='valid')
                # Find local maxima
                for i in range(1, len(smoothed) - 1):
                    if smoothed[i-1] < smoothed[i] > smoothed[i+1]:
                        if smoothed[i] > self.threshold_uv:
                            # Verify width of the peak (P300 is a broad wave, not a spike)
                            # This is a simplified heuristic
                            p300_events += 1
                            max_peak = max(max_peak, smoothed[i])
                            
        # De-duplicate blind scanning events heuristically
        if not event_markers:
            p300_events = min(p300_events, n_samples // self.window_size)

        risk_level = "LOW"
        if p300_events > 0:
            risk_level = "HIGH" if p300_events > 3 else "MEDIUM"

        return {
            "leakage_detected": p300_events > 0,
            "risk_level": risk_level,
            "p300_events_detected": p300_events,
            "max_p300_amplitude_uv": max_peak
        }
