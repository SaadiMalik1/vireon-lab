# VIREON Glossary & Formal Definitions

VIREON operates at the intersection of neuroscience, cybersecurity, and control theory. To maintain academic and engineering rigor, the following terms are formally defined within the scope of this repository.

> [!NOTE]
> VIREON is an **evolving research platform and reference implementation**. The phenomena described below are theoretical threat models designed for simulation and mitigation research, heavily inspired by the foundational work in the [qinnovates/neurosecurity](https://github.com/qinnovates/neurosecurity) repository.

## Neural Ransomware (QIF-T0002: Stimulation Leak)
**Formal Definition:** An attack vector where an adversary gains unauthorized write-access to an active neurostimulation implant (e.g., Deep Brain Stimulator) and modifies the stimulation parameters (amplitude, frequency, pulse width) beyond clinically safe limits, holding the cessation of the malicious stimulation hostage.
**Mathematical Bounds:** In VIREON, this is modeled as an override of the `DigitalTwin.stimulation_amplitude_ma` parameter where the demanded current $I_d$ exceeds the tissue safety threshold $I_{max} = 4.0\text{mA}$ or the cumulative charge density exceeds safe thermodynamic limits, forcing the Intrusion Prevention System (IPS) to enact a hard clamp.

## Unauthorized Cognitive State Inference
**Formal Definition:** The interception, decoding, and classification of raw electrophysiological telemetry (e.g., EEG, ECoG) by an unauthorized third party to infer sensitive patient states (e.g., P300 responses, emotional valence, motor intent).
**Context:** While the term implies "mind reading," in engineering practice, this refers to the compromise of the data confidentiality boundary at the BLE link layer or cloud endpoint, allowing classical machine learning classifiers to extract feature embeddings.

## Bifurcation Forcing / Pathological Synchronization
**Formal Definition:** An advanced closed-loop attack (QIF-T2301) where the adversary manipulates the sensed biomarker (e.g., Beta-band power) to force the PID or adaptive stimulation controller into a positive feedback loop, amplifying rather than suppressing the pathological state (e.g., Parkinsonian resting tremor).
**Mathematical Bounds:** Detected by the NeuroIDS when the variance of the beta power $\sigma^2_\beta$ diverges positively while the stimulation amplitude $A_s > 1.0\text{mA}$ over a continuous time window $t_w = 5\text{s}$.

## OSI of Mind Framework
A conceptual framework structuring neuro-cyber vulnerabilities across seven layers (from Physical Tissue to Application/Cognitive state), mirroring the traditional OSI model. Originally proposed in the [qinnovates/neurosecurity](https://github.com/qinnovates/neurosecurity) repository.

## qTARA (Quantitative Threat Assessment & Remediation Analysis)
A methodology and structured dataset for evaluating the severity and physical feasibility of neurosecurity threats, yielding a Neural Implant Severity Score (NISS). The VIREON repository uses a stubbed version of the 161-technique `qtara-registrar.json` datalake for simulation mapping.
