# Fast Fourier Transform (FFT)

## What is it?
The Fast Fourier Transform (FFT) is an algorithm that computes the discrete Fourier transform (DFT) of a sequence. In simpler terms, it takes a signal operating in the time domain (how voltage changes over time) and converts it into the frequency domain (how much of each specific frequency exists in that signal).

## Why does it matter?
Neural signals are overwhelmingly analyzed by their frequency bands (e.g., Alpha waves at 8-12 Hz, Beta waves at 13-30 Hz). FFT is the foundational mathematics that allows software to separate useful cognitive signals from baseline noise.

## Security considerations
Adversaries can craft attacks that exist invisibly in the time domain but are violently obvious in the frequency domain (or vice versa). Evasion techniques often attempt to inject noise that spreads evenly across frequencies to avoid triggering simple amplitude thresholds.

## Common vulnerabilities
- **Spectral Spoofing**: An attacker injecting specific frequencies (e.g., 10 Hz) into the sensor array to falsely trigger an Alpha-band classifier.

## Relevant standards
- None directly (mathematical principle).

## Open-source tools
- **NumPy**: `numpy.fft.rfft` is the standard for real-valued FFT computations in Python.
- **SciPy**: Advanced Welch's method for Power Spectral Density (PSD).

## Where VIREON uses this concept
The **Neuro Signal Assurance Engine (NSAE)** relies entirely on pure-NumPy FFT logic to dynamically calibrate baselines. It analyzes the spectral density of incoming EDF data to detect anomalous injections that fail to trigger standard time-domain (RMS) alarms.

## Further reading
- [Neuroscience: EEG](../neuroscience/eeg.md)
