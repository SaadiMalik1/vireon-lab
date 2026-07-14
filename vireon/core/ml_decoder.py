import numpy as np

class MLTremorDecoder:
    """
    Simulates a closed-loop neural tremor decoder.
    
    Processes LFP/EEG signal chunks, extracts time-domain RMS features,
    and classifies whether pathological tremors are active.
    """

    def __init__(self, sample_rate: int = 250, threshold: float = 5.0):
        self.sample_rate = sample_rate
        self.threshold = threshold

    def extract_features(self, chunk: np.ndarray) -> float:
        """
        Calculate the Root Mean Square (RMS) power of the signal chunk.
        """
        if chunk.size == 0:
            return 0.0
            
        if chunk.ndim > 1:
            signal = chunk[0, :]
        else:
            signal = chunk

        return float(np.sqrt(np.mean(signal ** 2)))

    def classify(self, power: float) -> bool:
        """
        Classifies whether pathological tremors are active based on RMS power.
        """
        return power > self.threshold


class AdversarialDefenseFilter:
    """
    Pure NumPy frequency-domain bandpass filter acting as an adversarial defense shield.
    
    Zeroes out frequencies outside the biological nominal range before signal features 
    are extracted by decoders, mitigating broadband noise injection attacks.
    """

    def __init__(self, sample_rate: int = 250, low_cut: float = 1.0, high_cut: float = 30.0):
        self.sample_rate = sample_rate
        self.low_cut = low_cut
        self.high_cut = high_cut

    def filter_signal(self, chunk: np.ndarray) -> np.ndarray:
        """
        Apply frequency-domain ideal bandpass filter.
        Works on single channel or multi-channel arrays of shape (channels, samples).
        """
        if chunk.size == 0:
            return chunk

        is_multichannel = chunk.ndim > 1
        data = chunk if is_multichannel else chunk[np.newaxis, :]
        
        n_channels, n_samples = data.shape
        if n_samples < 2:
            return chunk

        filtered_data = np.zeros_like(data)

        for ch in range(n_channels):
            signal = data[ch, :]
            # Perform Real FFT
            fft_vals = np.fft.rfft(signal)
            freqs = np.fft.rfftfreq(n_samples, d=1.0 / self.sample_rate)
            
            # Apply bandpass mask (zero out frequencies outside biological nominal band)
            mask = (freqs >= self.low_cut) & (freqs <= self.high_cut)
            fft_vals[~mask] = 0.0
            
            # Inverse FFT to reconstruct clean signal
            filtered_data[ch, :] = np.fft.irfft(fft_vals, n=n_samples)

        return filtered_data if is_multichannel else filtered_data[0, :]
