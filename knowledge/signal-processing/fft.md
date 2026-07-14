# Fast Fourier Transform (FFT)

## What is it?
The Fast Fourier Transform (FFT) is a computational algorithm that calculates the Discrete Fourier Transform (DFT) of a sequence. It converts a signal from the time domain (voltage amplitudes over time) into the frequency domain (spectral power distribution across frequency bins).

## Why does it matter?
Neural signals are inherently categorized by their frequency bands (e.g., Alpha: 8-12 Hz, Beta: 13-30 Hz, Gamma: >30 Hz). FFT is the foundational mathematics that allows neurotechnology software to isolate relevant biomarkers from baseline physiological noise and external artifacts.

## Security Considerations
Adversaries often craft attacks that remain statistically invisible in the time domain (e.g., matching normal RMS limits) but are distinctly anomalous in the frequency domain. Conversely, sophisticated evasion techniques attempt to spread injected noise evenly across multiple frequencies (white noise injection) to evade spectral detection thresholds.

## Common Vulnerabilities
- **Spectral Spoofing**: Injecting targeted frequencies (e.g., 20 Hz) into the sensor array to artificially inflate a specific biomarker (like beta power) and force a closed-loop response from a therapeutic device (such as Deep Brain Stimulation).

## Relevant Standards
- N/A (Mathematical Principle).

## Open-Source Tools
- **NumPy**: `numpy.fft.rfft` is the standard for real-valued FFT computations in Python, providing high performance for array-based digital signal processing.
- **SciPy**: Used for advanced Power Spectral Density (PSD) estimation, such as Welch's method (`scipy.signal.welch`).

## Where VIREON uses this concept
The **Deep Autoencoder IDS** (`vireon/core/security.py`) and the clinical emulators (e.g., `DBSEmulator` in `vireon/plugins/clinical/dbs_emulator.py`) rely heavily on FFT logic to dynamically extract spectral biomarkers and calibrate baselines. Specifically, the system analyzes the spectral density of incoming dataset streams to identify physical-layer anomalies that evade simple time-domain amplitude checks.

## Further reading
- [Neuroscience: EEG](../neuroscience/eeg.md)
- [Neuroscience: DBS](../neuroscience/dbs.md)
