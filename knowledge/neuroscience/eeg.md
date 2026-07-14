# Electroencephalography (EEG)

## What is it?
Electroencephalography (EEG) is a non-invasive method for recording the electrical activity of the brain. Electrodes are placed on the scalp to measure voltage fluctuations resulting from ionic current within the neurons of the brain.

## Why does it matter?
EEG is the most accessible modality for Brain-Computer Interfaces (BCIs). It is used to decode motor intentions, monitor sleep states, and diagnose epilepsy. Because it is non-invasive, it is highly prominent in commercial neurotechnology and consumer wearables.

## Security considerations
EEG signals represent highly sensitive biometric and cognitive data. An adversary with access to raw EEG can potentially infer a user's emotional state, medical conditions, or even subconscious reactions to external stimuli (e.g., subliminal attacks extracting PIN codes via P300 waves).

## Common vulnerabilities
- **Eavesdropping**: Unencrypted transmission of EEG data over Bluetooth Low Energy (BLE).
- **Signal Injection**: Introducing localized electromagnetic interference (EMI) that mimics physiological artifacts, tricking a BCI into executing an unauthorized command.
- **Spoofing**: Replaying a previously recorded "authorized" EEG session to bypass biometric authentication.

## Relevant standards
- **IEEE P2731**: Standard for a Unified Terminology for Brain-Computer Interfaces.
- **FDA**: Guidance on Software as a Medical Device (SaMD) evaluating EEG telemetry.

## Real devices
- **OpenBCI (Cyton/Ganglion)**
- **Emotiv EPOC**
- **Muse Headband**

## Research papers
- Refer to the PhysioNet dataset foundational paper tracked in `knowledge/papers/references.bib`.

## Open-source tools
- **MNE-Python**: Standard library for processing EEG arrays.
- **BrainFlow**: Hardware-agnostic EEG acquisition.

## Where VIREON uses this concept
In VIREON, the **Digital Twin** generates and hosts simulated EEG data structures (`vireon/core/data/`). The **Neuro Signal Assurance Engine (NSAE)** processes these arrays continuously, executing statistical checks to detect adversarial injection or spoofing within the EEG stream.

## Further reading
- [Signal Processing: Fast Fourier Transform (FFT)](../signal-processing/fft.md)
- [Protocols: Bluetooth Low Energy (BLE)](../protocols/ble.md)
