import numpy as np

def calculate_rms(signal: np.ndarray) -> float:
    """Calculates the Root Mean Square (RMS) of a 1D signal."""
    if len(signal) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(signal))))

def calculate_bandpower(signal: np.ndarray, sample_rate: int, band: tuple[float, float]) -> float:
    """
    Calculates the average power in a specific frequency band using FFT.
    Uses numpy FFT to avoid dependency on scipy.signal.
    """
    n = len(signal)
    if n == 0:
        return 0.0
    
    fft_vals = np.fft.rfft(signal)
    fft_freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
    
    psd = (np.abs(fft_vals) ** 2) / (sample_rate * n)
    
    idx = (fft_freqs >= band[0]) & (fft_freqs <= band[1])
    if not np.any(idx):
        return 0.0
        
    return float(np.mean(psd[idx]))
