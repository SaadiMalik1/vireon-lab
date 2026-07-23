# NL-002: Neural Signal Processing for Security Analysts (Part 1)

## 1. Overview

Signal processing is the computational backbone of every neurotechnology system. Raw neural signals — noisy, high-dimensional, information-dense — are useless without processing. Filtering removes interference. Feature extraction distills clinical biomarkers. Compression enables wireless transmission. Every transform changes the signal's representation, and every change in representation creates both a defense opportunity and a potential blind spot for security.

This module teaches signal processing not as an abstract discipline but as a security-critical engineering practice. You will learn to implement the same processing chains that run inside implantable pulse generators, external programmers, and BCI decoders — and you will learn to attack and defend each step.

The central thesis: **the signal processing pipeline is itself a trust boundary.** Data enters as raw samples and exits as features, decisions, or compressed packets. At each stage, an attacker can manipulate the data, the processing parameters, or the processing algorithm itself. Understanding these manipulation vectors requires understanding the processing chain in depth.

## 2. Historical Background

### 2.1 From Analog to Digital Neural Signal Processing

The history of neural signal processing parallels the history of digital computing, but with a 20-30 year delay due to the extreme computational demands of real-time neural data processing.

- **1960s-1970s:** Analog signal processing dominates. EEG machines use analog filters (RC circuits) for bandpass filtering. No digital storage — signals are written directly to paper. The only "processing" is analog filtering and amplification. Security is irrelevant because there is no digital representation to manipulate.

- **1980s:** Digital EEG becomes practical. ADCs with sufficient resolution (12-bit) and sampling rate (256 Hz) become affordable. Digital filtering replaces analog filters. The transition creates the first opportunity for digital manipulation of neural data, though the threat is not recognized for decades.

- **1990s:** Real-time digital signal processing becomes feasible on low-power processors. This enables implantable devices with digital processing (first generation of programmable DBS systems). The DSP algorithms running on these devices become part of the trusted computing base — but are not treated as security-critical.

- **2000s:** Advanced signal processing enters neurotechnology. Wavelet transforms for seizure detection. Independent component analysis (ICA) for artifact removal. Time-frequency analysis for neural oscillation characterization. These algorithms increase the information that can be extracted from neural signals — and consequently increase the impact of data exfiltration.

- **2010s:** Machine learning transforms neural signal processing. Deep learning classifiers for BCI. Adaptive filtering for closed-loop stimulation. The introduction of learned models creates new attack vectors (adversarial examples, model inversion, data poisoning) that did not exist in traditional DSP.

- **2020s:** Edge computing enables on-implant AI. Neuralink's N1 chip performs spike detection and feature extraction on the implant itself. The security boundary shifts — the attack target is no longer just the wireless link but the on-chip processing pipeline.

### 2.2 Security Implications of the Digital Transition

The transition from analog to digital processing created the fundamental preconditions for neurosecurity concerns:

1. **Digital representation enables manipulation.** An analog signal on a wire can be contaminated by noise but cannot be precisely edited. A digital signal in memory can be modified bit-by-bit with perfect precision.

2. **Programmability enables firmware attacks.** Analog circuits are fixed-function. Digital processors execute firmware, which can be replaced if the firmware update mechanism is compromised.

3. **Compression creates information loss.** Lossy compression removes information that an attacker might use to detect manipulation. The question becomes: does compression also remove the evidence of an attack?

4. **Feature extraction creates a semantic gap.** Raw samples and extracted features are different representations of the same data. An attack that is detectable in the raw domain may be invisible in the feature domain, and vice versa.

## 3. Scientific Foundations: Digital Signal Processing for Neural Data

### 3.1 Sampling Theorem and Its Security Implications

The Nyquist-Shannon sampling theorem states that a continuous signal can be perfectly reconstructed from its samples if the sampling rate is at least twice the highest frequency component. For neural signals:

- EEG: highest relevant frequency ~100 Hz → minimum sampling rate 200 Hz (clinical standard: 250-500 Hz)
- ECoG: highest relevant frequency ~500 Hz → minimum 1000 Hz (clinical: 500-2000 Hz)
- LFP: highest relevant frequency ~100 Hz → minimum 200 Hz (clinical: 250-500 Hz)
- Spike trains: action potential bandwidth ~6000 Hz → minimum 12000 Hz (clinical: 20,000-30,000 Hz)

**Security implications of sampling:**

An attacker who can control the ADC sampling rate (through firmware manipulation) can create aliasing — high-frequency interference that folds into the signal band after sampling. If the sampling rate is reduced below Nyquist, legitimate high-frequency neural activity (e.g., gamma oscillations in ECoG) aliases into lower frequencies and corrupts the signal. This is a denial-of-service attack that is difficult to detect because the corrupted signal appears to be low-frequency neural activity rather than obvious interference.

Conversely, oversampling (sampling well above Nyquist) provides a security benefit: it leaves headroom for detecting out-of-band energy that indicates EMI injection. If you sample at 1000 Hz but only use 0-100 Hz, the 100-500 Hz band serves as a canary — energy in this band indicates interference that should not be present after proper anti-aliasing. This is why VIREON's validation framework recommends oversampling by at least 2x when power budget allows.

### 3.2 Quantization and Its Information Impact

ADC resolution determines how precisely the analog signal is represented digitally. Clinical neural recording systems typically use 16-24 bit ADCs:

- 16-bit: 65,536 levels, LSB size = full-scale range / 65536
- 24-bit: 16,777,216 levels, LSB size = full-scale range / 16777216

For EEG with a ±500 uV input range:
- 16-bit: LSB = 1000/65536 ≈ 0.015 uV (sufficient — EEG noise floor is ~1 uV)
- 24-bit: LSB = 1000/16777216 ≈ 0.00006 uV (excessive — below thermal noise)

**Security implications:**

Quantization creates a noise floor that sets the minimum detectable signal change. An attacker's injection must exceed the quantization noise floor to have any effect. However, for 16-bit neural recording, the quantization noise (0.015 uV for EEG) is far below typical injection amplitudes, so quantization does not provide meaningful security. For spike trains, where the signal is larger (100-1000 uV), quantization is even less relevant.

Quantization is more security-relevant for **covert channel analysis.** If an attacker exfiltrates data by modulating stimulation parameters at sub-LSB levels, the modulation would be invisible to the 16-bit ADC but could potentially be detected by a higher-resolution analyzer. This is a theoretical attack vector that has not been demonstrated but is plausible for high-precision systems.

### 3.3 Windowing and Spectral Leakage

When computing the frequency content of a finite-length signal, we implicitly multiply the signal by a rectangular window. This causes spectral leakage — energy from one frequency spreads into adjacent frequencies, making it difficult to distinguish closely-spaced spectral components.

Window functions (Hann, Hamming, Blackman, etc.) reduce spectral leakage by tapering the signal edges to zero, at the cost of reduced frequency resolution. The choice of window function affects the ability to detect narrowband attacks:

- **Rectangular window:** Best frequency resolution, worst leakage. Can resolve closely-spaced spectral peaks but also creates sidelobes that obscure weak signals.
- **Hann window:** Good compromise. Reduces sidelobes by ~31 dB compared to rectangular. Standard choice for neural signal PSD estimation.
- **Blackman window:** Best sidelobe suppression (~58 dB) but worst frequency resolution. Used when detecting weak signals near strong ones.

**Security implications:**

An attacker injecting a narrowband signal (e.g., a 50 Hz powerline interference attack) wants the injection to be as narrowband as possible to minimize detectability. The analyst's window function choice affects detectability: a Hann window will spread the attack energy across neighboring frequencies, potentially making it harder to distinguish from legitimate neural activity. A rectangular window will show the attack as a sharp spectral line, making it more detectable.

VIREON's spectral analysis tools should use multiple window functions and compare results. If an anomaly appears with one window but not another, it may indicate a narrowband injection that is being masked by windowing. This multi-window approach is a defense-in-depth strategy for spectral attack detection.

## 4. Digital Filtering: The First Processing Layer

### 4.1 Why Neural Signals Must Be Filtered

Raw neural signals after digitization contain multiple contaminating signals:

- **Powerline interference (50/60 Hz):** Electromagnetic coupling from power lines. Typically 10-100 uV in EEG, can exceed neural signal amplitude.
- **DC offset:** The electrode-tissue junction creates a DC potential (up to several hundred mV for some electrode types) that must be removed to avoid saturating amplifiers.
- **Low-frequency drift:** Slow changes in electrode impedance, skin potentials (for EEG), or tissue response create drift below 0.5 Hz.
- **High-frequency noise:** Electronic noise from the amplifiers (thermal, 1/f), environmental EMI.
- **Physiological artifacts:** Eye movements, muscle activity (EMG), cardiac signal (ECG), respiration.

Filtering removes these contaminations. The filter design determines what is removed and what is preserved — and therefore what attacks are detectable after filtering.

### 4.2 Filter Types and Their Security Properties

#### High-Pass Filter (removes low frequencies)

**Purpose:** Remove DC offset and low-frequency drift.
**Typical cutoff:** 0.5-1 Hz for EEG, 1-2 Hz for LFP.
**Implementation:** Butterworth or Bessel, 2nd-4th order.

**Security implication:** A high-pass filter with a 0.5 Hz cutoff removes very slow signal variations. An attacker who injects a very low-frequency signal (<0.5 Hz) to manipulate a baseline or drift-sensitive metric will have their injection removed by this filter. This is actually a defense — the high-pass filter rejects out-of-band attacks. However, it also means that very slow parameter manipulation (changing a signal's mean over tens of seconds) would be invisible to any analysis that operates only on high-pass filtered data.

#### Low-Pass Filter (removes high frequencies)

**Purpose:** Remove high-frequency noise and prevent aliasing.
**Typical cutoff:** 40-100 Hz for EEG (clinical), up to 500 Hz for ECoG.
**Implementation:** Butterworth or Bessel, 4th-8th order.

**Security implication:** A low-pass filter with a 40 Hz cutoff removes all activity above 40 Hz. This includes gamma-band activity (30-100 Hz) which carries information in ECoG and research EEG. For an attacker, this means that any injection above 40 Hz will be removed. Conversely, if the low-pass cutoff is set too aggressively (e.g., 30 Hz for an EEG system that should preserve gamma), the filter itself is causing information loss that an attacker could exploit — if the system is designed to never see gamma, an attacker can inject gamma-band energy without fear of detection.

#### Bandpass Filter (combination)

**Purpose:** Isolate the frequency band of interest.
**Typical bands:** Delta (0.5-4 Hz), Theta (4-8 Hz), Alpha (8-13 Hz), Beta (13-30 Hz), Gamma (30-100 Hz).
**Implementation:** Cascaded high-pass and low-pass, or a single bandpass design.

**Security implication:** Bandpass filters are the primary tool for feature extraction in neural signal processing. In closed-loop DBS, the beta band (13-30 Hz) power is the biomarker that controls stimulation. The bandpass filter that isolates beta is therefore a critical security component:

- If the beta bandpass filter has a design flaw (e.g., too wide a passband that includes adjacent frequencies), an attacker could inject energy at adjacent frequencies that leak into the beta estimate.
- If the filter order is too low (poor roll-off), out-of-band energy from an attack will not be sufficiently attenuated.
- If the filter has a phase distortion, the temporal structure of the beta oscillation is altered, which could affect a closed-loop controller that depends on phase-locked stimulation.

#### Notch Filter (removes a specific frequency)

**Purpose:** Remove powerline interference (50 or 60 Hz) and harmonics.
**Implementation:** IIR notch (2nd order), or adaptive notch.

**Security implication:** This is the most security-critical filter in many neural systems. An attacker who injects energy at exactly the notch frequency will have their injection removed — but an attacker who injects at 49.5 Hz (just below a 50 Hz notch) will have their injection preserved. The narrowness of the notch determines how precisely the attacker must target their injection frequency.

More critically: **an attacker can weaponize the notch filter.** If an attacker injects a strong 50 Hz signal that overwhelms the neural signal, the notch filter will remove it — but the notch filter may also remove legitimate neural activity that happens to be at 50 Hz (rare in scalp EEG, but possible in ECoG where powerline artifact can mix with neural activity through volume conduction). This is an availability attack: force the system to apply aggressive notching, which removes legitimate signal.

Additionally, an adaptive notch filter (which tracks the exact interference frequency) can be manipulated: if the attacker slowly sweeps the injection frequency, the adaptive filter will follow it, potentially removing a wider range of frequencies than intended.

### 4.3 IIR vs. FIR Filters: Security Trade-offs

| Property | IIR (Infinite Impulse Response) | FIR (Finite Impulse Response) |
|---|---|---|
| Order needed for sharp cutoff | Low (4th-6th) | High (100th-500th) |
| Computational cost | Low | High |
| Phase response | Non-linear (phase distortion) | Can be exactly linear |
| Stability | Can be unstable | Always stable |
| Memory | Requires feedback (state) | No feedback |
| Security: parameter tampering | Dangerous — instability can crash firmware | Safer — bounded output for bounded input |
| Security: covert channel | Feedback state could leak information | No state, no covert channel |
| Security: implementation complexity | Higher (coefficient precision matters) | Lower |

**For VIREON:** FIR filters are preferred for security-critical applications because they are unconditionally stable and have no hidden state. IIR filters are commonly used in implantable devices due to their lower computational cost, but their instability risk and state-dependent behavior make them harder to validate. VIREON's validation framework should flag IIR filter usage and require additional stability analysis.

### 4.4 Filter Implementation Vulnerabilities

**Coefficient quantization:** Filter coefficients are stored with finite precision (typically 32-bit float in firmware). Quantization can cause the actual filter response to deviate from the designed response. For IIR filters, coefficient quantization can push poles closer to the unit circle, reducing stability margin. An attacker who understands the coefficient format could potentially craft an input that exploits the quantization-induced deviation.

**Overflow and saturation:** In fixed-point implementations (common in implantable DSP), filter computations can overflow. If overflow is not handled correctly (wraparound vs. saturation), it can produce large output spikes that propagate through the processing chain. This is a firmware vulnerability that can be triggered by a specific input pattern.

**Filter state manipulation:** IIR filters maintain internal state (previous input and output samples). If an attacker can write to the filter state (through a firmware vulnerability), they can cause the filter to produce arbitrary output. This is a more subtle attack than direct data injection because the attack occurs inside the processing pipeline rather than at the input.

## 5. Artifact Detection and Classification

### 5.1 What Are Artifacts?

Artifacts are signals recorded by the electrodes that do not originate from neural activity. They contaminate the neural signal and must be detected and either removed or flagged. Artifacts are security-relevant because they can be weaponized (an attacker can inject artificial artifacts) and because they can mask attacks (an artifact removal algorithm might remove evidence of an injection).

### 5.2 Artifact Types and Their Security Implications

#### Eye Blink and Eye Movement Artifacts (EEG)

**Characteristics:** 100-300 uV, 1-3 Hz, primarily anterior channels (Fp1, Fp2). Duration: 200-400 ms for blinks, 100-300 ms for saccades.

**Detection methods:** Amplitude threshold on anterior channels, correlation with reference EOG channels, template matching.

**Security implication:** An attacker who can inject a signal that mimics an eye blink artifact will trigger the artifact rejection algorithm, causing the system to discard the contaminated data segment. This is a **denial-of-service attack on the data** — the system loses neural data during the artifact window. If the artifact rejection is overly aggressive (flagging many false positives), the attacker can cause significant data loss by injecting frequent low-amplitude blink-like signals.

More subtly, an attacker could inject an artifact that is **just below the detection threshold.** The artifact would not be flagged but would still corrupt the underlying neural signal. This is a **data integrity attack** that exploits the gap between the artifact's actual impact and the detection algorithm's sensitivity.

#### Muscle (EMG) Artifacts

**Characteristics:** Broadband (20-300 Hz), high amplitude (can exceed 1000 uV), primarily temporal and neck channels.

**Detection methods:** High-frequency power ratio, spectral analysis above 30 Hz.

**Security implication:** EMG artifacts overlap with the beta and gamma bands that are clinically significant. An attacker who injects broadband noise that mimics EMG will corrupt the beta/gamma power estimates used by closed-loop controllers. Because the injected signal resembles a legitimate artifact, it may not be flagged as anomalous. This is particularly dangerous for closed-loop DBS systems that use beta power as a biomarker — the attacker can inflate beta power to suppress stimulation (denial of therapy) or depress beta power to trigger unnecessary stimulation.

#### Cardiac (ECG) Artifacts

**Characteristics:** Periodic (1-1.5 Hz), sharp QRS complex, predominantly in electrodes near vasculature.

**Detection methods:** Template matching with QRS templates, correlation with reference ECG.

**Security implication:** ECG artifacts are highly stereotyped and periodic. An attacker who injects a periodic signal at the cardiac frequency could trigger ECG artifact rejection, causing systematic data loss synchronized with the heartbeat. This would selectively remove time-locked neural activity (e.g., heartbeat-evoked potentials), potentially biasing any analysis that depends on cardiac synchronization.

#### Electrode Pop Artifacts

**Characteristics:** Sudden DC offset shift, followed by exponential recovery. Caused by sudden impedance changes at the electrode-tissue interface.

**Detection methods:** Amplitude derivative (sudden jumps), DC level monitoring.

**Security implication:** Electrode pop artifacts are particularly dangerous because they indicate a potential hardware problem (loose electrode, tissue reaction). An attacker who can inject a signal that mimics an electrode pop could trigger a device alarm or cause the system to disable the affected channel. In a multi-channel BCI, disabling channels reduces the system's capability — a denial-of-service attack at the channel level.

### 5.3 Artifact Removal Methods and Their Security Implications

#### Rejection (zeroing out artifact segments)

**Method:** Detect artifact time windows and set the signal to zero during those windows.

**Security implication:** Creates data gaps that an attacker can exploit. If the system fills gaps with interpolation, the interpolated values are predictable and can be replaced without detection. If gaps are left empty, downstream processing must handle missing data — the handling method may create exploitable patterns.

#### ICA (Independent Component Analysis)

**Method:** Decompose multi-channel data into independent components, identify artifact components by their topology and spectral characteristics, and remove them.

**Security implication:** ICA assumes that neural sources and artifact sources are statistically independent. An attacker who injects a signal that is statistically correlated with neural activity will not be separated by ICA — the attack will survive artifact removal. This is a more sophisticated attack than simple injection because it requires the attacker to understand the statistical structure of the neural signal.

Additionally, ICA itself can be attacked. If an attacker can manipulate the input to ICA (e.g., by injecting specific patterns into specific channels), they can influence the component decomposition, potentially causing legitimate neural components to be misclassified as artifacts and removed. This is a **data integrity attack through artifact removal manipulation.**

#### Adaptive Filtering

**Method:** Use a reference signal (e.g., EOG electrode for eye artifacts) to estimate the artifact contribution and subtract it.

**Security implication:** If the reference signal is compromised (an attacker injects a false reference), the adaptive filter will subtract the wrong thing — removing legitimate neural signal and leaving the artifact. This is an attack on the reference channel that propagates through the adaptive filter to corrupt all channels.

#### Wavelet-Based Denoising

**Method:** Decompose the signal using the wavelet transform, threshold small coefficients (assumed to be noise), and reconstruct.

**Security implication:** The thresholding step is a decision boundary. Coefficients below the threshold are removed, coefficients above are preserved. An attacker who crafts an injection whose wavelet coefficients are just above the threshold will have their attack preserved. An attacker whose injection coefficients are below the threshold will have their attack removed. The threshold choice is therefore a security parameter — VIREON should validate that the wavelet threshold preserves attack signatures while removing noise.

## 6. Signal Quality Assessment

### 6.1 Why Signal Quality Matters for Security

Signal quality metrics provide the first line of defense against signal manipulation. A sudden change in signal quality (increased noise, changed impedance, shifted frequency content) may indicate an attack. However, signal quality metrics can also be subverted — an attacker who gradually degrades the signal can desensitize quality monitors (a "boiling frog" attack).

### 6.2 Key Quality Metrics

**Signal-to-Noise Ratio (SNR):** The ratio of signal power to noise power, typically in dB. For EEG, good SNR is >10 dB. For spike trains, >20 dB.

**Security implication:** An EMI injection attack will change the SNR. If the attacker injects a signal that is correlated with the neural signal (e.g., a replay attack), the SNR may not change significantly — the attacker's signal adds to the neural signal rather than adding uncorrelated noise. SNR alone cannot detect replay attacks.

**Electrode Impedance:** The AC impedance at the electrode-tissue interface, measured in kOhm. Typical EEG: 1-10 kOhm. High impedance (>50 kOhm for EEG) indicates poor contact and increased noise vulnerability.

**Security implication:** Impedance is typically measured at the start of a recording session and monitored periodically. A sudden impedance change may indicate electrode manipulation (physical attack) or tissue changes (post-surgical healing, scarring). An attacker who can manipulate the impedance measurement (through firmware) can mask a physical attack or trigger a false alarm (desensitizing the monitor).

**Line Noise Level:** The power at 50/60 Hz relative to the total signal power.

**Security implication:** Elevated line noise may indicate EMI injection. However, line noise also varies with environmental factors (proximity to electrical equipment, grounding quality). A gradual increase in line noise could be either an escalating attack or a legitimate environmental change. Distinguishing between these requires context that the signal processing pipeline alone cannot provide.

**Signal Flatness:** The proportion of the signal that is at or near the ADC's maximum amplitude (clipping). Clipping indicates saturation, which may be caused by an injection that exceeds the amplifier's input range.

**Security implication:** An attacker who injects a large-amplitude signal to cause clipping is performing a denial-of-service attack on the signal quality. However, clipping is also detectable — the flat-topped waveform is clearly non-physiological. A more sophisticated attacker would inject at an amplitude just below the clipping threshold, maximizing impact while avoiding detection.

### 6.3 VIREON Signal Quality Validation

VIREON's validation framework should require the following signal quality checks for any neural signal processing pipeline:

1. **SNR monitoring:** Alert if SNR changes by more than 6 dB from baseline within a 10-second window.
2. **Impedance monitoring:** Alert if any channel's impedance changes by more than 20% from the session baseline.
3. **Line noise monitoring:** Alert if 50/60 Hz power exceeds 10% of total power.
4. **Clipping detection:** Alert if more than 0.1% of samples are at ADC limits.
5. **Stationarity check:** Alert if signal statistics (mean, variance) change significantly over time (using a sliding-window KS test).
6. **Cross-channel consistency:** Alert if the correlation between adjacent channels changes by more than 30% from baseline.

These checks are implemented as a VIREON validation provider in Lab 001.
