# NL-002: Neural Signal Processing for Security Analysts (Part 2)

## 7. Feature Extraction: Where Processing Becomes Decision-Making

### 7.1 What Are Features?

Features are computationally derived quantities that summarize the raw signal in a way that is relevant to the application. In neural signal processing, features bridge the gap between raw voltage samples and clinical decisions. The feature extraction step is where the signal is reduced from thousands of samples per second to a handful of numbers that drive the system's behavior.

This reduction is precisely why feature extraction is security-critical. An attack that is detectable in the raw domain may be invisible after feature extraction (the attack was "compressed away"). Conversely, an attack on the feature values themselves (rather than the raw signal) can control the system's behavior with minimal changes to the raw data.

### 7.2 Time-Domain Features

#### Band Power

**What it is:** The total power in a specified frequency band, computed by integrating the power spectral density over the band.

**How it works:**
1. Apply a bandpass filter to isolate the frequency band of interest
2. Compute the power in the filtered signal: P = (1/N) * sum(x^2)
3. Alternatively, compute the PSD (via Welch's method) and integrate over the band

**Why it matters clinically:** Beta-band (13-30 Hz) power in the STN is the primary biomarker for closed-loop DBS in Parkinson's disease. When beta power is high, stimulation is increased. When beta power is low, stimulation is decreased. The entire closed-loop control algorithm depends on this single number.

**Security analysis:**
- Band power is a **summary statistic** — it discards phase information, temporal structure, and spectral detail within the band. An attacker who injects energy at any frequency within the beta band will increase the beta power estimate, regardless of whether the injection is a pure sinusoid (obviously artificial) or a realistic oscillation (harder to detect).
- The time window used for band power computation determines the temporal resolution of the closed-loop system. A 1-second window means the controller updates once per second — the system cannot respond faster than this. An attacker who manipulates the signal on a sub-second timescale may not be detected by a system that only evaluates band power once per second.
- The bandpass filter parameters (cutoff frequencies, order, type) determine what energy counts as "beta." If the filter's transition band is wide, out-of-band energy leaks into the beta estimate. An attacker can exploit this by injecting energy at frequencies just outside the nominal beta band.

**VIREON validation:** VIREON should validate that the band power computation is reproducible (same input produces same output), accurate (matches a reference implementation), and robust (small perturbations of the input produce small changes in the output).

#### Hjorth Parameters

**What they are:** Three time-domain parameters that characterize a signal's statistical properties:
1. **Activity:** The variance of the signal (total power)
2. **Mobility:** The square root of the ratio of the variance of the first derivative to the variance of the signal. Represents the mean frequency.
3. **Complexity:** The ratio of the mobility of the first derivative to the mobility of the signal. Represents how much the frequency content changes.

**Security analysis:**
- Hjorth parameters are computationally cheap (no FFT required), making them attractive for implantable devices with limited processing power. However, their simplicity also makes them easier to manipulate. An attacker who understands the mathematical definitions can craft inputs that produce arbitrary Hjorth parameter values.
- Activity is just variance — adding any constant offset does not change it (after DC removal). An attacker who adds a constant to the signal (DC offset injection) will not affect activity, but will affect other downstream processing that expects zero-mean input.
- Mobility depends on the first derivative. An attacker who adds high-frequency noise will increase the first derivative variance, increasing mobility. This changes the system's estimate of the signal's dominant frequency without actually changing the frequency content of the neural signal — a semantic attack.

#### Line Length

**What it is:** The sum of absolute differences between consecutive samples: LL = sum(|x[i] - x[i-1]|).

**Security analysis:** Line length is sensitive to both amplitude and frequency — higher amplitude and higher frequency both increase line length. An attacker who injects a high-frequency, low-amplitude signal can increase line length without significantly affecting band power. This creates a discrepancy between the two features that an anomaly detector could flag. VIREON's multi-feature validation approach exploits exactly this kind of cross-feature inconsistency.

### 7.3 Frequency-Domain Features

#### Spectral Edge Frequency (SEF)

**What it is:** The frequency below which a specified percentage of the total power is contained. SEF50 is the median frequency; SEF90/SEF95 are commonly used in anesthesia monitoring (BIS monitor).

**Security analysis:** SEF is a single number that summarizes the entire spectrum. An attacker who injects energy at a specific frequency can shift the SEF by changing the power distribution. For anesthesia monitoring (where SEF90 drives the bispectral index), manipulating SEF could cause the system to incorrectly estimate the patient's depth of anesthesia — a direct patient safety concern.

#### Spectral Entropy

**What it is:** The Shannon entropy of the normalized power spectrum. High entropy indicates a flat, noise-like spectrum. Low entropy indicates a peaked spectrum with dominant frequencies.

**Security analysis:** An attacker injecting a narrowband signal (e.g., a pure sinusoid) will decrease spectral entropy — the spectrum becomes more peaked. This is detectable as an anomaly if the baseline entropy is known. However, if the attacker injects a broadband signal that matches the neural signal's spectral shape, the entropy change may be negligible.

### 7.4 Feature-Level Attacks

Feature extraction creates a new attack surface that does not exist at the raw signal level:

**Feature spoofing:** Instead of injecting a signal that produces the desired feature value, the attacker directly modifies the feature value in memory (through a firmware vulnerability). This bypasses all signal-domain defenses because the attack occurs after feature extraction.

**Feature manipulation through parameter tampering:** If the feature extraction parameters (filter coefficients, window length, frequency bands) are stored in modifiable memory, an attacker who changes these parameters can alter the feature computation without touching the signal or the feature values. For example, changing the beta band from 13-30 Hz to 30-50 Hz would cause the closed-loop controller to respond to gamma-band activity instead of beta-band activity.

**Feature replay:** Recording the feature values during a legitimate session and replaying them later. Since features are low-dimensional (a few numbers per update), they are easy to replay. The system receives plausible feature values but the underlying neural state has changed.

## 8. Time-Frequency Analysis

### 8.1 Why Time-Frequency Analysis Matters for Security

The Fourier transform provides the frequency content of the entire signal but loses temporal information. A 10-second recording has one spectrum — it cannot tell you when a specific frequency component appeared or disappeared. For security, this is a limitation because attacks may be transient (lasting milliseconds) and would be averaged out in a full-signal FFT.

Time-frequency analysis preserves both temporal and spectral information, enabling detection of transient attacks that are invisible to standard spectral analysis.

### 8.2 Short-Time Fourier Transform (STFT)

**What it is:** The signal is divided into short segments (windows), and the FFT is computed for each segment. The result is a 2D representation: frequency vs. time.

**Parameters:**
- Window length: Determines the trade-off between time and frequency resolution (Heisenberg uncertainty). Shorter windows = better time resolution, worse frequency resolution.
- Overlap: Consecutive windows typically overlap by 50-75% to improve temporal smoothness.
- Window function: Hann, Hamming, etc. (see Section 3.3).

**Security application:** An attacker who injects a brief burst of energy (e.g., a 50 ms pulse at 50 Hz) will appear as a localized energy increase in the time-frequency plane. The STFT reveals both the frequency (50 Hz) and the timing (the specific 50 ms window) of the attack. Standard FFT over the entire recording would show elevated 50 Hz power but not when it occurred.

**Attack detection with STFT:**
1. Compute STFT of the monitored signal
2. For each time-frequency bin, compare the power against a baseline (learned from clean data)
3. Flag bins that exceed the baseline by more than a threshold
4. Analyze the spatial pattern of flagged bins: a single frequency appearing suddenly is more suspicious than a gradual broadband increase

### 8.3 Continuous Wavelet Transform (CWT)

**What it is:** The signal is convolved with a set of wavelets (oscillatory functions with finite duration) at different scales. The result is a time-frequency representation with frequency-dependent time resolution — high frequencies have better time resolution than low frequencies.

**Advantages over STFT:**
- Better time resolution at high frequencies (important for detecting short-duration high-frequency attacks)
- Better frequency resolution at low frequencies (important for resolving closely-spaced low-frequency components)
- The wavelet basis functions are better matched to the transient, oscillatory nature of neural signals

**Security application:** Wavelet analysis is particularly effective for detecting transient attacks because the wavelet basis naturally captures transient events. A brief EMI pulse, a momentary frequency shift, or a sudden amplitude change will produce a localized response in the wavelet domain that is easy to detect and localize.

### 8.4 Hilbert Transform and Instantaneous Phase

**What it is:** The Hilbert transform constructs the analytic signal from a real-valued signal, enabling computation of the instantaneous amplitude, frequency, and phase.

**Security application:** Phase-locked stimulation is an emerging closed-loop DBS technique where stimulation pulses are delivered at a specific phase of the neural oscillation. The Hilbert transform computes the instantaneous phase that drives the phase-locked controller. An attacker who can manipulate the Hilbert transform output (by injecting a signal that biases the phase estimate) can cause stimulation to be delivered at the wrong phase — potentially reducing therapeutic efficacy or causing side effects.

The Hilbert transform is also useful for detecting replay attacks: if the instantaneous phase of a replayed signal is compared to the expected phase evolution, discontinuities at the splice points will be detectable as sudden phase jumps.

### 8.5 Spectrogram Anomaly Detection

VIREON's approach to time-frequency-based attack detection:

1. Compute the STFT spectrogram of the input signal
2. Apply a logarithmic compression (log(1 + |STFT|)) to reduce dynamic range
3. Compute a baseline spectrogram from clean reference data (mean and std per time-frequency bin)
4. Compute the z-score of each bin: z = (current - mean) / std
5. Flag bins where |z| > 3 (3-sigma rule)
6. Analyze the spatial pattern of flagged bins:
   - **Narrowband transient:** Single frequency, brief duration → likely EMI injection
   - **Broadband transient:** All frequencies, brief duration → likely electrode pop or connection issue
   - **Narrowband sustained:** Single frequency, long duration → likely powerline interference (or sustained injection)
   - **Broadband sustained:** All frequencies, long duration → likely increased noise (environmental or attack)

This classification enables automated attack triage without human intervention, suitable for VIREON's real-time validation pipeline.

## 9. Spike Detection and Sorting

### 9.1 The Spike Detection Pipeline

Spike detection is the process of identifying action potentials (spikes) in a continuous neural recording. The pipeline consists of:

1. **Bandpass filtering:** 300-6000 Hz to isolate spike bandwidth
2. **Thresholding:** Detect events that exceed a threshold (typically 3-5x RMS noise)
3. **Alignment:** Align detected events to their peak or trough
4. **Feature extraction:** Extract waveform features (peak amplitude, trough amplitude, width, etc.)
5. **Clustering:** Group similar waveforms into putative single units
6. **Classification:** Assign detected spikes to identified units

### 9.2 Security Implications of Spike Processing

**Threshold manipulation:** The detection threshold determines which events are classified as spikes. An attacker who lowers the threshold will cause noise events to be classified as spikes, degrading the quality of the sorted data (integrity attack). An attacker who raises the threshold will cause small but real spikes to be missed, reducing the apparent firing rate (integrity attack on the firing rate estimate).

**Clustering manipulation:** Spike sorting relies on the assumption that spikes from the same neuron have similar waveforms. An attacker who injects artificial spikes with waveforms that fall between two clusters can cause misclassification, corrupting the unit-specific firing rate estimates that drive BCI decoders.

**Template poisoning:** Some spike sorting systems use template matching (comparing detected waveforms against stored templates). If the attacker can modify the templates (through firmware access), they can cause the system to accept injected waveforms as legitimate or reject legitimate waveforms as artifacts.

### 9.3 Spike Train Security Properties

Spike trains have unique security properties compared to continuous signals:

- **Discrete event representation:** Spikes are discrete events, not continuous values. This makes traditional signal processing attacks (amplitude scaling, frequency injection) inapplicable. Attacks must operate on the event times and waveforms.

- **Point process statistics:** Spike trains are analyzed as point processes (Poisson, renewal, etc.). The statistical properties (firing rate, interspike interval distribution, autocorrelation) are the features that must be protected.

- **High bandwidth:** At 30 kS/s with 16-bit resolution, spike data generates 480 kbps per channel. This is 120x the data rate of EEG at 250 S/s. The high bandwidth constrains real-time security processing.

## 10. Neural Data Compression

### 10.1 Why Compression Matters

Wireless neural data transmission is power-constrained. Every bit transmitted consumes battery energy. Compression reduces the number of bits, extending battery life. However, compression also removes information — and the removed information may include attack artifacts.

### 10.2 Compression Methods

**Lossless compression:** Huffman coding, Lempel-Ziv, FLAC-style. No information loss. Typical compression ratio for neural signals: 1.5-2.5x. Requires the receiver to decompress before processing.

**Lossy compression:** Quantization, downsampling, transform coding (DCT, wavelet). Information is permanently lost. Typical compression ratio: 5-20x. The compressed data can be processed directly.

**Feature-level compression:** Instead of transmitting raw samples, transmit extracted features (band power, spike times). Extreme compression (100-1000x) but loses all information not captured by the features.

### 10.3 Security Implications of Compression

**Lossy compression can mask attacks.** If an attack artifact has the same statistical properties as quantization noise, the compression will remove it. For example, a low-amplitude sinusoidal injection at a frequency between two DCT coefficients will be split between adjacent coefficients and may fall below the quantization threshold — the attack is compressed away.

**Compression creates a semantic gap.** The compressed representation is a different signal than the original. Security analysis performed on the compressed signal may miss attacks that are visible in the original. VIREON's validation framework should analyze security at multiple representation levels (raw, filtered, compressed, feature).

**Compression parameters are security-critical.** The compression ratio, quantization step size, and transform type determine what information is preserved. An attacker who can modify these parameters can control what information survives compression — a feature-level attack on the compression pipeline.

### 10.4 VIREON Compression Validation

VIREON should validate that the compression pipeline:
1. Preserves clinically relevant features (band power estimates are accurate to within 5% after compression/decompression)
2. Preserves attack detectability (attacks that are detectable in the raw signal are also detectable in the compressed signal, or the compression is flagged as security-inadequate)
3. Does not introduce artifacts that could be confused with attacks (compression artifacts should be distinguishable from injection artifacts)

## 11. Practical Signal Processing Pipeline for VIREON

### 11.1 Reference Pipeline Architecture

The following pipeline represents a complete neural signal processing chain suitable for VIREON's digital twin input processing:

```
Raw Samples (from NL-001 Simulator or hardware provider)
    |
    v
[Quality Check] — SNR, impedance, clipping, line noise
    |                If quality check fails: flag and optionally reject
    v
[DC Removal] — High-pass filter at 0.5 Hz (IIR, 2nd order Butterworth)
    |
    v
[Notch Filter] — Remove 50/60 Hz (IIR, 2nd order notch)
    |
    v
[Artifact Detection] — Amplitude threshold, spectral analysis
    |                    If artifact detected: flag segment
    v
[Quality Metrics Computation] — SNR, band powers, line noise, stationarity
    |
    v
[Output: Processed Signal + Quality Report]
```

This pipeline is implemented in Lab 001 as a reusable VIREON provider.

### 11.2 Security Checkpoints

Each stage of the pipeline has a security checkpoint:

1. **Input validation:** Verify that the input is within the expected amplitude range and sampling rate. Reject inputs that are clearly non-physiological (e.g., all zeros, constant value, full-scale).

2. **Post-filter quality check:** Verify that filtering has not degraded SNR by more than 3 dB (excessive degradation may indicate filter instability or parameter tampering).

3. **Post-artifact-detection consistency check:** Verify that the artifact detection rate is within expected bounds (0-30% of data flagged for EEG, 0-10% for invasive recordings). An anomalously high artifact rate may indicate an attack.

4. **Feature consistency check:** Verify that extracted features are consistent with each other (e.g., beta power and spectral edge frequency should correlate). Inconsistencies may indicate manipulation.

## 12. Relations to Subsequent Modules

NL-002's signal processing knowledge feeds into:

- **NL-003 (Firmware):** The DSP algorithms described here run on the implant's MCU. Understanding them is essential for firmware analysis and reverse engineering.

- **NL-004 (Wireless):** The processed signal is what gets transmitted. Understanding the signal's properties (data rate, information content) is essential for evaluating wireless protocol security.

- **NL-005 (Closed-Loop):** The features extracted here (band power, spectral features) are what drive the closed-loop controller. Feature manipulation is the primary attack vector on closed-loop systems.

- **NL-006 (Adversarial ML):** The ML classifiers in BCI systems operate on features extracted by the pipeline described here. Understanding feature extraction is essential for understanding adversarial example attacks on BCI classifiers.