# NL-001 References

## Foundational Papers (Must Read)

1. **Halperin, D., Heydt-Benjamin, T.S., Ransford, B., Clark, S.S., Defend, B., Morgan, W., Fu, K., Kohno, T., & Maisel, W.H. (2008).** "Pacemakers and Implantable Cardiac Defibrillators: Software Radio Attacks and Zero-Power Defenses." *IEEE Symposium on Security and Privacy (S&P)*.
   - **Why:** Established the methodology for wireless medical device security research. Every subsequent neurosecurity paper builds on this approach.
   - **VIREON Relevance:** The attack methodology (protocol RE, replay, command injection) is the basis for VIREON's protocol security validation providers.

2. **Martinovic, I., Davies, D., Frank, M., Perito, D., Ros, T., & Song, D. (2012).** "On the Feasibility of Side-Channel Attacks with Brain-Computer Interfaces." *USENIX Security Symposium*.
   - **Why:** Demonstrated that EEG signals contain private information (typed keys, viewed images). Established neural data as a privacy-sensitive biometric.
   - **VIREON Relevance:** Directly motivates VIREON's data privacy validation requirements.

3. **Ali, S., Gao, Y., Aboalsamh, H., & Bhatti, A. (2020).** "A Survey of Brain-Computer Interface Security and Privacy." *IEEE Access*, 8, 140038-140055.
   - **Why:** Comprehensive survey establishing the modern taxonomy of BCI security threats. Essential reading for anyone entering the field.
   - **VIREON Relevance:** The threat taxonomy aligns with VIREON's threat modeling framework.

## Signal Processing Papers

4. **Nunez, P.L. & Srinivasan, R. (2006).** *Electric Fields of the Brain: The Neurophysics of EEG.* Oxford University Press.
   - **Why:** The definitive reference on the physics of neural signal generation and volume conduction.

5. **Buzsaki, G. (2012).** *Rhythms of the Brain.* Oxford University Press.
   - **Why:** Essential neuroscience foundation for understanding neural signal origins and their functional significance.

6. **Quiroga, R.Q. (2012).** "Spike sorting." *Current Opinion in Neurobiology*, 22(4), 557-564.
   - **Why:** Spike sorting is the process of assigning detected spikes to individual neurons. Security-relevant because it determines the information content of spike train data.

7. **Nuwer, M.R., et al. (1998).** "IFCN Standard for Digital Recording of Clinical EEG." *International Federation of Clinical Neurophysiology*.
   - **Why:** Defines the technical standards for clinical EEG recording, including sampling rates, bandwidth, and artifact handling.

## Adversarial ML Papers

8. **Zhang, H., Wang, Z., & Liu, J. (2019).** "Adversarial Attacks on EEG-Based Brain-Computer Interfaces." *IEEE Transactions on Neural Systems and Rehabilitation Engineering*, 27(9), 1842-1851.
   - **Why:** Demonstrated that small perturbations to EEG signals cause BCI misclassification. Multiple paradigms affected.
   - **VIREON Relevance:** Directly motivates VIREON's adversarial robustness validation requirements for BCI decoders.

9. **Majumdar, A., et al. (2020).** "Adversarial Robustness of Neural Signal Classifiers: A Systematic Evaluation." *Journal of Neural Engineering*.
   - **Why:** Systematic evaluation showing that most BCI classifiers are highly vulnerable and that adversarial training provides only marginal improvement.

## Medical Device Security Papers

10. **Kim, K., Ransford, B., & Kohno, T. (2012).** "A Systematic Review of Implantable Medical Device Security." *ACM Computing Surveys*.
    - **Why:** Comprehensive taxonomy of attack surfaces and defenses for implantable devices. Identified the lack of standardized assessment methodologies.
    - **VIREON Relevance:** This gap is what VIREON's validation framework is designed to fill.

11. **Li, C., Raghunathan, A., & Jha, N.K. (2016).** "Hacking Medical Devices: Safety vs. Security." *IEEE Security & Privacy*, 14(6), 60-65.
    - **Why:** Discusses the tension between safety (FDA requirement) and security (often neglected). The safety monitor provides defense-in-depth but has significant limitations.

12. **Son, S., et al. (2019).** "Security Analysis of Cochlear Implant Programming Protocol." *IEEE TNSRE*.
    - **Why:** Demonstrated that cochlear implant programming commands can be intercepted and modified.

## Neural Data Privacy Papers

13. **LaRue, S.S., et al. (2020).** "Brain Data Privacy: Challenges and Opportunities." *IEEE Signal Processing Magazine*, 37(5), 48-58.
    - **Why:** Comprehensive analysis of what can be inferred from neural signals and current privacy protections. Identified that neural data can reveal information the person may not be consciously aware of.

14. **Wu, J., et al. (2020).** "EEG-based User Identification: A Deep Learning Approach." *IEEE TIFS*.
    - **Why:** Demonstrated >95% individual identification accuracy from EEG, establishing neural signals as biometric identifiers.

## Books

1. **Buzsaki, G.** *Rhythms of the Brain.* — Neural oscillations and their functional significance.
2. **Nunez, P.L. & Srinivasan, R.** *Electric Fields of the Brain.* — Physics of neural signal generation.
3. **Tompkins, W.J.** *Biomedical Digital Signal Processing.* — Practical signal processing for biomedical signals.
4. **Shostack, A.** *Threat Modeling: Designing for Security.* — Applied threat modeling methodology (STRIDE).
5. **Anderson, R.** *Security Engineering.* — Comprehensive security reference including medical devices.
6. **Dang, B., et al.** *Practical Reverse Engineering.* — Firmware RE techniques applicable to neural implants.
7. **Cormen, T.H., et al.** *Introduction to Algorithms.* — Reference for cryptographic algorithm analysis.

## Standards and Regulations

| Standard | Description | Relevance |
|---|---|---|
| IEC 62443 | Industrial automation security | Increasingly referenced for medical device cybersecurity |
| IEC 60601-1-6 | Medical electrical equipment usability | Relevant for human factors in security (emergency access) |
| IEC 80001-1 | Risk management for IT-networks with medical devices | Network security for medical device ecosystems |
| FDA Cyber Guidance (2023) | Premarket cybersecurity requirements | Requires threat modeling, risk analysis, and testing for FDA submission |
| ISO 14971 | Medical device risk management | Framework for identifying and managing risks, including security risks |
| ISO 27001 | Information security management | Applicable to IT infrastructure supporting neurotechnology |
| HIPAA | US health data privacy | Protects neural data as protected health information |
| GDPR (EU) | Data protection regulation | Classifies neural data as health data and biometric data |
| FCC Part 95 | MICS band regulations | Regulatory requirements for implant communication spectrum |
| ETSI EN 301 839 | MICS equipment standards | Technical requirements for MICS-band medical devices |
| IEC 62304 | Medical device software lifecycle | Software development process requirements |
| AIMD (FDA) | Amendments to IMD regulations | Security-specific requirements for implantable devices |

## Open-Source Projects

| Project | URL | Purpose |
|---|---|---|
| BrainFlow | https://brainflow.org/ | Open-source BCI library, multi-device signal acquisition |
| MNE-Python | https://mne.tools/ | EEG/MEG data analysis, essential for neural signal processing |
| GNU Radio | https://www.gnuradio.org/ | Software-defined radio framework, essential for RF security research |
| Ghidra | https://ghidra-sre.org/ | NSA's open-source reverse engineering tool for firmware analysis |
| OpenBCI | https://openbci.com/ | Open-source EEG hardware and software |
| HackRF | https://greatscottgadgets.com/hackrf/ | Low-cost SDR for medical device RF research |
| Frida | https://frida.re/ | Dynamic instrumentation toolkit for runtime firmware analysis |
| Binwalk | https://github.com/ReFirmLabs/binwalk | Firmware analysis and extraction |
| Scipy | https://scipy.org/ | Scientific computing, signal processing |
| PyRFSimulator | Various | Python-based RF protocol simulation tools |

## Public Datasets

| Dataset | URL | Content | Security Relevance |
|---|---|---|---|
| PhysioNet TUH EEG | https://physionet.org/content/tuh-eeg/ | 10,000+ clinical EEG recordings | Reference for physiological signal validation |
| BCI Competition | http://www.bbci.de/competition/ | Motor imagery, P300, SSVEP BCI data | BCI decoder evaluation |
| EEG Motor Movement | https://physionet.org/content/eegmmidb/ | 109 subjects, 14 experimental runs | Biometric identification research |
| Sleep-EDF | https://physionet.org/content/sleep-edf/ | Sleep EEG with staging annotations | Signal processing validation |
| CRCNS | https://crcns.org/ | Spike trains, LFP from animal studies | Intracranial signal validation |
| MNE Sample Data | Built into MNE-Python | Example EEG/MEG datasets | Tutorial and validation |
| Kaggle EEG | Various | Seizure detection, emotion recognition | ML classifier evaluation |
| TUH Abnormal EEG | https://isip.piconepress.com/projects/tuh_eeg/html/tuh_eeg_abnormal.shtml | Normal vs. abnormal EEG | Anomaly detection evaluation |