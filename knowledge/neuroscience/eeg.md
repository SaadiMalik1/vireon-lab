# Electroencephalography (EEG): The Non-Invasive Attack Surface

Electroencephalography (EEG) measures macroscopic voltage fluctuations on the scalp resulting from the synchronized ionic currents of millions of cortical neurons. In the context of neurosecurity, EEG represents the most accessible, high-noise, and low-spatial-resolution interface available.

## 1. The Physics of EEG (Signal Degradation)

Unlike invasive modalities (such as ECoG or intracortical arrays), EEG signals must travel through the meninges, cerebrospinal fluid, skull, and scalp before reaching the electrode. 

- **Spatial Blurring**: The skull acts as a severe low-pass spatial filter. A highly localized cortical signal (e.g., motor intent) spreads out, resulting in poor spatial resolution ($>1\text{cm}$).
- **Signal Attenuation**: The high electrical resistance of the skull severely attenuates the signal, dropping amplitudes from millivolts (at the cortex) to microvolts ($\mu\text{V}$) at the scalp.
- **Frequency Constraints**: High-frequency bands (Gamma, $>30\text{Hz}$) are exceptionally vulnerable to attenuation and muscle artifact interference.

*Relevance to VIREON*: When simulating an EEG BCI, the `DigitalTwin` must apply rigorous low-pass filtering and spatial blurring functions. If an attacker injects a highly localized, high-frequency, high-amplitude signal into an EEG feed, our `NeuroethicsGuardrails` and NSAE (Neuro Signal Assurance Engine) should flag it as biologically impossible.

## 2. Threat Vectors and Vulnerabilities

Because EEG signals are extremely weak (typically $10–100\mu\text{V}$), the amplification hardware (e.g., ADCs, op-amps) is highly sensitive. This creates unique physical-layer vulnerabilities:

- **Electromagnetic Interference (EMI) Injection**: An attacker in close physical proximity can broadcast specific RF frequencies that resonate with the EEG leads (which act as antennas). This injected noise can overpower the $\mu\text{V}$-level biological signal, causing a Denial of Service.
- **Subliminal Evoked Potentials (P300 Spying)**: A compromised application (e.g., a VR game) can flash stimuli at a user while recording their EEG. The P300 event-related potential acts as an involuntary "recognition" signal, allowing the attacker to extract subconscious preferences, familiar faces, or PIN codes.
- **Signal Spoofing**: Because EEG data is heavily pre-processed and classified by machine learning models (e.g., CNNs for motor imagery), injecting a carefully crafted adversarial perturbation can force the BCI to misclassify the user's intent with high confidence.

## 3. Modeling EEG Defenses

Defending an EEG-based system requires multi-layered signal processing:

1. **Galvanic Isolation**: Ensuring the physical hardware is isolated to prevent malicious power surges from harming the user.
2. **Impedance Monitoring**: Continuously checking electrode-skin impedance. A sudden change may indicate physical tampering or hardware degradation.
3. **Artifact Rejection**: Using algorithms (like Independent Component Analysis - ICA) to separate true neural signals from eye blinks, muscle noise (EMG), and 60Hz powerline interference. 

In VIREON, the `NSAE` pipeline implements spectral anomaly detection to identify injected EMI artifacts that fall outside typical biological frequency distributions.
