# NL-001: Neural Signals & The Neurosecurity Problem Space

> **Module ID:** NL-001 | **Track:** Foundations | **Version:** 1.0

---

## 1. Overview

Neurosecurity is the application of cybersecurity principles to neurotechnology — the devices, systems, and algorithms that interact with the nervous system. This module establishes the foundational knowledge required to reason about neurosecurity: what neural signals are, how they are acquired and processed, what systems handle them, and why these systems present unique security challenges.

This is not a module about neuroscience for its own sake. Every concept introduced here is framed by its security implications. The amplitude of an EEG signal matters because it defines the noise floor that an attacker must overcome for signal injection. The bandwidth of a neural recording matters because it determines the data rate that the wireless link must support, which constrains the cryptographic overhead that can be tolerated. The spatial resolution of ECoG matters because it determines how precisely an attacker must target electromagnetic interference to inject a specific false signal.

The central thesis of this module: **neural data is not merely medical data — it is a data type with unique security properties that emerge from its biological origin, its clinical significance, its information density, and the life-safety context in which it is processed.** Standard medical device security approaches, while necessary, are insufficient for neurotechnology. Understanding why requires understanding what neural signals are.

## 2. Historical Background

### 2.1 Neural Recording: From Animal Electricity to Implantable Chips

The history of neural recording spans centuries, but the security-relevant history begins with the development of technologies that created digital representations of neural activity — because digital representations can be intercepted, modified, and replayed.

- **1924**: Hans Berger records the first human EEG, demonstrating that electrical activity can be measured non-invasively from the scalp. The signals are analog, recorded photographically. No digital security concerns exist because the data has no digital representation.

- **1950s-1960s**: Development of microelectrode techniques allows recording of single-neuron action potentials (spike trains) in animals. Hubel and Wiesel's work on visual cortex neurons demonstrates the information richness of individual neural signals. The data is still primarily analog.

- **1970s-1980s**: Digital signal processing becomes practical. ADCs with sufficient resolution and sampling rate become available for neural signals. The transition from analog to digital representation creates the fundamental precondition for all modern neurosecurity concerns — data that exists as bits can be manipulated as bits.

- **1990s**: Cochlear implants become commercially successful. These are among the first widely deployed neural interface devices with wireless programming capability. The wireless programming interface, designed for clinical convenience, simultaneously creates the first widespread wireless attack surface on a neural device.

- **1997**: FDA approves the first deep brain stimulation (DBS) system (Medtronic Activa) for essential tremor. DBS implants are wirelessly programmable, creating a permanent, life-critical wireless attack surface inside the patient's body.

- **2000s**: Brain-computer interface (BCI) research accelerates. The BrainGate project demonstrates that paralyzed patients can control a computer cursor using intracortical recordings. The clinical motivation for BCIs creates pressure to deploy them, but the security implications of high-bandwidth neural data transmission are not yet addressed.

- **2008**: Halperin et al. demonstrate wireless attacks on implantable cardiac devices using a software-defined radio. This paper does not target neural devices directly, but it establishes the methodology — protocol reverse engineering, replay attacks, command injection — that all subsequent neural implant security research builds on. This is the paper that made the medical device security field credible.

- **2012**: Martinovic et al. demonstrate that EEG signals recorded during typing contain enough information to reconstruct typed text. This establishes neural signals as a side-channel for private information leakage, expanding the security concern beyond device security to data security.

- **2016**: Security researchers demonstrate vulnerabilities in Abbott's (St. Jude Medical) implantable device ecosystem. The FDA issues a safety advisory. This is the first major regulatory response to neural device security vulnerabilities.

- **2019-present**: Adversarial machine learning research demonstrates that BCI systems are vulnerable to adversarial examples. Neuralink receives FDA breakthrough device designation. The field of neurosecurity is established but fragmented — no standardized assessment methodology exists. This is the gap VIREON is designed to fill.

### 2.2 Security Evolution in Medical Devices

Medical device security has evolved through distinct phases, each driven by external pressure:

- **Phase 1 (pre-2008): Security through obscurity.** Proprietary protocols, assumed physical proximity, no published attacks. The prevailing belief was that the short range and low power of implant telemetry provided sufficient security.

- **Phase 2 (2008-2014): Academic awareness.** The Halperin et al. paper and subsequent research demonstrated that attacks were feasible. Manufacturers began adding basic security (authentication, encryption) to new devices. Legacy devices remained vulnerable.

- **Phase 3 (2014-2023): Regulatory response.** FDA issues cybersecurity guidance for pre-market submissions. IEC 62443 is increasingly referenced. Security becomes a regulatory requirement, but the requirements are generic and the enforcement is inconsistent.

- **Phase 4 (2023-present): Maturation attempt.** Updated FDA guidance, growing academic community, increasing public awareness. But the fundamental challenges remain: device lifecycle mismatch, resource constraints, lack of standardized validation methodology.

## 3. Scientific Foundations

### 3.1 The Biophysical Basis of Neural Signals

Neurons communicate through electrochemical signaling. The electrical component — the action potential (spike) — is the primary signal recorded by neurotechnology. Understanding the biophysics is security-relevant because it defines the physical layer that all security mechanisms are built on top of.

**Resting membrane potential:** Neurons maintain a ~-70 mV potential difference across their cell membrane, established by the Na+/K+ ATPase pump and differential membrane permeability to ions. This potential exists because the membrane is a dielectric barrier separating two conducting solutions (intracellular and extracellular fluid) with different ionic compositions. The resting potential is the baseline from which all neural signals deviate.

**Action potential generation:** When a neuron receives sufficient excitatory input, voltage-gated Na+ channels open, Na+ rushes in, the membrane depolarizes rapidly to ~+40 mV, then voltage-gated K+ channels open, K+ rushes out, and the membrane repolarizes and briefly hyperpolarizes. This ~1 ms event is the action potential — the fundamental unit of neural communication. From a security perspective, the action potential is the highest-bandwidth, highest-spatial-resolution neural signal and the most information-rich.

**Synaptic transmission:** The action potential triggers neurotransmitter release at the axon terminal. Neurotransmitters bind to receptors on the postsynaptic neuron, causing excitatory or inhibitory postsynaptic potentials (EPSPs/IPSPs). These graded potentials (typically 0.1-10 mV) decay over time and distance. They are not typically recorded directly in clinical neurotechnology but contribute to the field potentials recorded by EEG, ECoG, and LFP electrodes.

### 3.2 Volume Conduction

The electrical signals generated by neurons propagate through biological tissue to reach recording electrodes. This propagation is called volume conduction, and it is the physical process that determines what a recording electrode actually measures.

The key principle: **an electrode does not record the activity of a single neuron (unless it is a microelectrode placed inside or immediately adjacent to the neuron).** Instead, it records the weighted sum of all electrical activity in the surrounding tissue, with weighting determined by the distance from each neural source to the electrode and the conductivity of the intervening tissue.

The implications for security:

- **Spatial blurring:** Volume conduction blurs the spatial specificity of neural signals. An EEG electrode records the summed activity of millions of neurons spread across several square centimeters of cortex. An attacker attempting to inject a spatially specific signal through EMI must overcome this blurring — the injected signal will be distributed across the volume conductor, not focused on a single electrode.

- **Frequency-dependent attenuation:** High-frequency signals (action potentials) attenuate more rapidly with distance than low-frequency signals (synaptic potentials). This is why EEG primarily reflects low-frequency (0.5-100 Hz) activity — the high-frequency components are attenuated before reaching the scalp. For security, this means that spike-train-level attacks require closer proximity to the neural source than EEG-level attacks.

- **Reference-dependent measurement:** All electrical recordings are differential — they measure the potential difference between two points. The choice of reference electrode affects the recorded signal. An attacker who can influence the reference electrode can effectively modify all channel recordings.

### 3.3 Signal Modality Taxonomy

The four primary neural signal modalities, in order of decreasing spatial resolution and increasing invasiveness:

#### EEG (Electroencephalography)
- **What it is:** Recording of summed postsynaptic potentials from the cortical surface, measured non-invasively from the scalp.
- **Typical amplitude:** 10-100 uV (microvolts)
- **Bandwidth:** 0.5-100 Hz (clinical), up to 500 Hz (research)
- **Spatial resolution:** ~1-2 cm (limited by skull attenuation and volume conduction)
- **Invasiveness:** Non-invasive (surface electrodes)
- **What it reflects:** Synchronized cortical activity — rhythms, evoked potentials, event-related potentials
- **Clinical uses:** Epilepsy diagnosis, sleep staging, coma assessment, brain death determination
- **Security relevance:** Widely deployed in consumer devices (Muse, Emotiv, OpenBCI). The consumer application creates a large attack surface. EEG data contains enough information for biometric identification and cognitive state inference. The low amplitude makes it susceptible to EMI injection. The non-invasive nature means no surgical barrier to electrode access.

#### ECoG (Electrocorticography)
- **What it is:** Recording from electrodes placed directly on the cortical surface (under the skull but outside the pia mater). Requires craniotomy.
- **Typical amplitude:** 50-500 uV
- **Bandwidth:** 0.5-500 Hz (clinical), up to several kHz (research)
- **Spatial resolution:** ~1-5 mm (much better than EEG because the skull is bypassed)
- **Invasiveness:** Semi-invasive (requires craniotomy, electrodes on brain surface)
- **What it reflects:** Local cortical field potentials with better spatial specificity than EEG
- **Clinical uses:** Epilepsy seizure focus localization (intraoperative), functional brain mapping
- **Security relevance:** Used in research BCIs (higher signal quality than EEG). The implanted nature means the electrode location is fixed, providing spatial stability. The higher signal quality means more information can be extracted, increasing the impact of data exfiltration.

#### LFP (Local Field Potential)
- **What it is:** Recording of summed neural activity in a local brain region, typically from depth electrodes (e.g., DBS leads used for recording). Measures the same biophysical phenomenon as EEG/ECoG but from within the brain parenchyma.
- **Typical amplitude:** 100-1000 uV
- **Bandwidth:** 0.5-500 Hz (most analysis focuses on 0.5-200 Hz)
- **Spatial resolution:** ~1-3 mm (depends on electrode size and location)
- **Invasiveness:** Invasive (electrodes penetrate brain tissue)
- **What it reflects:** Local population neural activity, oscillatory dynamics in deep brain structures
- **Clinical uses:** DBS lead localization, biomarker identification for closed-loop stimulation (e.g., beta-band power in subthalamic nucleus for Parkinson's disease)
- **Security relevance:** LFP is increasingly used in closed-loop DBS systems (Medtronic Percept PC, Abbott Infinity). The recorded LFP drives the stimulation algorithm. If an attacker can inject false LFP data, they can manipulate the closed-loop controller. This is one of the most security-critical signal modalities because it directly controls a therapeutic intervention.

#### Spike Trains (Single-Unit / Multi-Unit Activity)
- **What it is:** Recording of individual action potentials (spikes) from one or a few neurons. Requires microelectrodes placed within or immediately adjacent to neurons.
- **Typical amplitude:** 100-1000 uV (extracellular)
- **Bandwidth:** 300-6000 Hz (action potential bandwidth)
- **Spatial resolution:** Single-neuron (theoretical), practically multi-neuron (50-200 um)
- **Invasiveness:** Highly invasive (microelectrodes in brain tissue)
- **What it reflects:** Individual neuron firing patterns — the most information-rich neural signal
- **Clinical uses:** Research BCIs (BrainGate), experimental neuroprosthetics
- **Security relevance:** The highest-bandwidth neural signal. Neuralink's high-channel-count system records spike data. The information density makes spike data the most valuable target for exfiltration (it encodes detailed motor intentions, sensory representations, and potentially cognitive content). However, the high bandwidth requirements make secure transmission more challenging (more data to encrypt, authenticate, and protect).

## 4. Engineering Foundations

### 4.1 Neural Data Acquisition Pipeline

Every neurotechnology system implements a version of the following pipeline. Understanding this pipeline is essential because each stage represents a potential attack surface and a potential validation point.

```
Neural Source (neurons)
    |
    v
[Electrodes] — transduce ionic current to electronic current
    |
    v
[Analog Front-End (AFE)] — amplify (10,000-100,000x), filter, impedance matching
    |
    v
[ADC] — digitize (16-24 bit, 500 Hz - 30 kS/s depending on modality)
    |
    v
[Digital Signal Processing] — notch filter (powerline), bandpass, artifact removal
    |
    v
[Feature Extraction / Compression] — reduce data rate for transmission
    |
    v
[Encryption / Authentication] — protect data for wireless transmission
    |
    v
[RF Telemetry] — transmit wirelessly (BLE, MICS, proprietary)
    |
    v
[External Receiver / Programmer] — decrypt, authenticate, display
    |
    v
[Clinical Application / Cloud Storage / BCI Decoder]
```

Each stage has security-relevant properties:

- **Electrodes:** Physical interface to neural tissue. Vulnerable to EMI injection at the electrode-tissue interface. The electrode-tissue impedance is a physiological parameter that can be measured remotely — changes in impedance may indicate electrode migration (failure mode) or tampering.

- **AFE:** High-gain amplification means any interference injected before the AFE is amplified along with the neural signal. The AFE's input impedance and noise performance determine the minimum detectable signal and therefore the minimum signal an attacker must inject to be effective.

- **ADC:** The ADC's resolution and sampling rate determine the dynamic range and bandwidth of the digitized signal. Quantization noise from the ADC sets a noise floor that affects signal quality and the detectability of subtle attacks.

- **Digital Signal Processing:** DSP firmware is a potential attack surface. Buffer overflows in filter implementations could compromise the entire system. DSP parameters (filter coefficients, notch frequency) could be manipulated to alter the recorded signal.

- **Feature Extraction:** Data compression and feature extraction reduce the information content. This can be either a security feature (less data to exfiltrate) or a security risk (compression artifacts could mask attack indicators).

- **Encryption/Authentication:** The cryptographic layer. Its correctness, completeness, and implementation quality determine the security of the wireless link.

- **RF Telemetry:** The wireless link. Its protocol, modulation, and implementation determine the attack surface accessible to a remote attacker.

### 4.2 Implantable Pulse Generator (IPG) Architecture

The IPG is the core implanted component in most neurostimulation systems. It is a hermetically sealed titanium capsule containing:

- **Microcontroller (MCU):** Executes firmware for signal acquisition, processing, stimulation control, and telemetry. Typically ARM Cortex-M class. Power-constrained.

- **Analog Front-End (AFE) ASIC:** Custom-designed integrated circuit for neural signal amplification and digitization. The AFE is the interface between the biological and digital domains.

- **RF Telemetry Module:** Implements the wireless protocol for communication with the external programmer. Typically operates in the MICS band (402-405 MHz) for implantable devices.

- **Stimulation Circuitry:** Constant-current or constant-voltage sources that generate therapeutic stimulation pulses. Connected to the electrodes through the lead.

- **Battery:** Primary (non-rechargeable, 3-9 year life) or secondary (rechargeable, weekly/daily charging). The battery is the primary constraint on all design decisions — power determines what computations are feasible.

- **Safety Monitor:** Independent hardware circuit that enforces hard limits on stimulation parameters (voltage, current, charge, duty cycle). Cannot be bypassed by firmware.

Understanding the IPG architecture is essential for security analysis because the trust boundaries, attack surfaces, and defense mechanisms are all determined by this architecture.

## 5. Medical Foundations

### 5.1 Clinical Applications of Neurotechnology

Neurosecurity cannot be understood without understanding the clinical context. The clinical application determines:
- What neural signals are recorded
- What stimulation is delivered
- What the consequences of a security failure would be
- What safety mechanisms exist
- What regulatory constraints apply

#### Deep Brain Stimulation (DBS)

**Indication:** Parkinson's disease, essential tremor, dystonia, obsessive-compulsive disorder, epilepsy, treatment-resistant depression (investigational).

**Mechanism:** Electrodes are surgically implanted into deep brain structures (subthalamic nucleus, globus pallidus interna, ventral intermediate nucleus of thalamus). Continuous high-frequency electrical stimulation (130-185 Hz) modulates pathological neural circuit activity. The exact mechanism is still debated — proposed mechanisms include local inhibition, axonal activation, and network desynchronization.

**Device architecture:** The IPG is typically implanted in the chest wall (subclavicular), similar to a cardiac pacemaker. Leads extend from the IPG to the brain through a subcutaneous tunnel. The lead contains 4-8 electrodes at the distal tip. The IPG contains the battery, MCU, AFE, RF telemetry, and stimulation circuitry.

**Patient lifecycle:**
1. **Diagnosis:** Patient is diagnosed with a movement disorder
2. **Surgical implantation:** Lead placement under stereotactic guidance, IPG implantation in chest
3. **Initial programming:** First programming session 2-4 weeks post-surgery
4. **Titration:** Multiple programming sessions over months to optimize parameters
5. **Maintenance:** Periodic programming adjustments, battery replacement surgery every 3-9 years
6. **Device explant:** Device is surgically removed (end of life, infection, or patient decision)

**Security relevance at each lifecycle stage:**
- **Surgical implantation:** Physical access to device. An attacker with surgical access could tamper with the device before implantation (supply chain attack). The surgical procedure itself creates a window where the device is unpowered and unmonitored.
- **Initial programming:** First wireless session. If the device has no pre-installed security credentials (some legacy devices), this session may establish credentials insecurely. The programming session must occur in a clinical setting, which provides some physical security.
- **Titration:** Multiple programming sessions create multiple opportunities for attack. Each session is a window where the device is in a higher-power communication mode and more receptive to commands.
- **Maintenance:** Battery replacement surgery requires the device to be powered down and may involve firmware updates. This is a high-risk lifecycle stage from a security perspective.
- **Device explant:** Device is surgically removed. Data on the device must be securely erased. **Some devices retain therapy history that could be extracted.**

## 6. Clinical Relevance

The clinical relevance of neurosecurity is not theoretical. Documented clinical consequences of medical device cyberattacks include:

- **ICD reprogramming** causing inappropriate shocks (theoretical demonstration, no known clinical incidents — but the theoretical pathway is validated)
- **Insulin pump manipulation** causing hypoglycemia (demonstrated by researchers, FDA recall issued for the Animas OneTouch Ping)
- **Hospital network breaches** exposing patient neural data (multiple documented incidents through ransomware attacks on hospital networks, including the 2017 WannaCry impact on UK NHS hospitals where neuroimaging and EEG data was potentially exposed)

For neural implants specifically, the clinical consequences of a successful attack depend on the device type and the attack's nature:

| Attack Type | Clinical Consequence | Severity |
|---|---|---|
| Data exfiltration | Privacy breach, neural pattern exposure | Medium |
| Stimulation parameter modification | Therapeutic failure or direct harm | High-Critical |
| Firmware manipulation | Full device control, arbitrary stimulation | Critical |
| Battery drain attack | Loss of therapy, emergency surgery required | High |
| Replay attack | Incorrect parameter delivery, unintended state change | Medium-High |
| Denial of service | Loss of therapy, patient harm from underlying condition | High |
| EMI injection at electrode | False signal generation, closed-loop malfunction | High |

## 7. Current Industry Practice

### 7.1 Major Neurotechnology Manufacturers

**Medtronic:** Largest manufacturer of implantable neural devices (DBS, SCS, cochlear implants via subsidiary). Uses proprietary MICS-band telemetry (402-405 MHz). Authentication in newer systems uses challenge-response with AES-128. Older systems used minimal or no authentication. Security through obscurity was the dominant approach until approximately 2015. The Medtronic InterStim (sacral neuromodulation) and Activa (DBS) lines represent the largest deployed base of wirelessly programmable neural implants globally.

**Abbott (formerly St. Jude Medical):** Manufacturer of DBS (Infinity system) and SCS (Proclaim system). The Merlin@home transmitter was found vulnerable in 2016 — researchers from MedSec and investment firm Muddy Waters demonstrated remote compromise of the transmitter, which could then relay malicious commands to the implant. This led to FDA advisory and mandatory firmware updates. The Abbott case is significant because it demonstrated that the attack surface includes not just the implant-programmer link but the entire ecosystem including home monitoring equipment.

**Boston Scientific:** DBS (Vercise system) and SCS (WaveWriter system). Uses proprietary telemetry with improving security posture. Less publicly documented security research than Medtronic or Abbott, which does not imply better security — it implies less scrutiny.

**Cochlear Ltd:** Leading cochlear implant manufacturer (Nucleus system). Uses a proprietary RF link for programming. Security research has shown that the wireless programming interface can be intercepted and that stimulation parameters can be modified. The clinical consequence is non-life-threatening but includes potential for auditory discomfort or device malfunction.

**Neuralink:** High-bandwidth intracortical BCI. Architecture is less publicly documented but known to use a custom wireless link from the implanted N1 chip to an external receiver. As a first-generation device with FDA breakthrough device designation, cybersecurity documentation is required but the actual security posture is not publicly verifiable. The high bandwidth (reportedly 1024 channels at 20 kS/s each) creates a data exfiltration concern that exceeds any previous neural implant.

**Blackrock Neurotech:** Research-grade intracortical recording systems (Utah array). Used in BrainGate and other academic BCI systems. Security engineering is minimal — these are research devices, not commercial products. The transition of this technology from research to clinical use (as BrainGate approaches FDA approval) creates a security gap.

**Synchron:** Endovascular BCI (Stentrode). Placed in the jugular vein, positioned in the superior sagittal sinus to record motor cortex activity. Uses Bluetooth for data transmission. The endovascular approach means the device is not implanted in the brain parenchyma, reducing surgical risk but maintaining the same wireless attack surface.

### 7.2 Industry Security Patterns

The current industry approach to neurotechnology security follows an uneven trajectory that reflects the broader medical device industry's security maturation:

- **Legacy devices (pre-2015):** Minimal security. Proprietary protocols with no authentication, no encryption, no integrity protection. Assumed physical proximity provided sufficient security. These devices are still implanted in patients and will remain in service for years.

- **Current devices (2015-present):** Improving but inconsistent. Most new device submissions to FDA now include cybersecurity risk analysis per the 2014 FDA pre-market guidance. Most implement some form of authentication and encryption, but implementation quality varies significantly. Some devices use AES-128 but with hardcoded keys. Some implement authentication but only unidirectional (programmer authenticates to implant, but implant does not verify programmer). Some use encryption but without replay protection.

- **Next-generation devices (in development):** Designed with security from the ground up. Secure boot, hardware security modules (HSMs), mutual authentication, end-to-end encryption, forward secrecy. But these are still in development or early deployment, and the security claims have not been independently validated by third parties.

The fundamental industry problem: **device lifecycles are 5-15 years, but security best practices evolve much faster.** A device implanted in 2020 may still be in a patient in 2035, running firmware that was state-of-the-art in 2019. The cryptographic algorithms, key lengths, and protocol designs that were acceptable at implantation may be breakable by the time the device is explanted. There is currently no mechanism for meaningful security updates to most implanted devices — firmware updates, where supported, are rare and patients must visit a clinic. VIREON's validation approach must account for this lifecycle mismatch and provide security assessment that is meaningful at the time of implantation and throughout the device's service life.

## 8. Academic State of the Art

### 8.1 Key Research Contributions

**Medical device security (foundational, non-neural but methodologically essential):**

- **Halperin et al. (2008)** — "Pacemakers and Implantable Cardiac Defibrillators: Software Radio Attacks and Zero-Power Defenses." Demonstrated wireless attacks on implantable cardiac devices using a software-defined radio. Established the methodology — protocol reverse engineering, replay attacks, command injection — that all subsequent neural implant security research builds on. The zero-power defense concept (device goes silent when it detects excessive RF energy) is relevant to neural implants.

- **Kim et al. (2012)** — "Implantable Medical Device Security: A Systematic Review." Comprehensive taxonomy of attack surfaces and defenses for implantable devices. Identified that the lack of standardized security assessment methodologies is a fundamental gap.

**Neural implant security (specific):**

- **Koris et al. (2017)** — Security analysis of neurostimulators. Focused on DBS systems, demonstrated that stimulation parameters could be wirelessly modified. Identified that the safety monitor in the IPG provides some defense against out-of-range parameters but cannot detect in-range-but-wrong parameters.

- **Ali et al. (2020)** — "A Survey of Brain-Computer Interface Security and Privacy." Comprehensive identification of threat categories including signal injection, data exfiltration, adversarial examples, and model inversion. This paper established the modern taxonomy of BCI security threats.

- **Martinovic et al. (2012)** — "My Brain Knows What You're Typing: A Novel Keylogging System Based on Brain-Computer Interfaces." Demonstrated that EEG signals contain enough information to extract private data (keystrokes, PINs, banking information). This established neural data as a privacy-sensitive biometric that goes beyond traditional medical data concerns.

**Adversarial machine learning on neural data:**

- **Zhang et al. (2019)** — "Adversarial Attacks on EEG-Based Brain-Computer Interfaces." Demonstrated that small, imperceptible perturbations to EEG signals could cause misclassification in BCI decoders. The adversarial perturbations were successful across multiple BCI paradigms (motor imagery, P300, SSVEP).

- **Majumdar et al. (2020)** — "Adversarial Robustness of Neural Signal Classifiers: A Systematic Evaluation." Systematic evaluation of attack and defense methods. Found that most BCI classifiers are highly vulnerable to adversarial examples and that adversarial training provides only marginal improvement.

**Neural data privacy:**

- **LaRue et al. (2020)** — "Brain Data Privacy: Challenges and Opportunities." Comprehensive analysis of what can be inferred from neural signals (cognitive states, emotional responses, neurological conditions, identity) and current privacy protection methods. Identified that neural data is uniquely sensitive because it can reveal information that the person themselves may not be consciously aware of.

### 8.2 Research Gaps

- **Formal verification of neural implant firmware:** No published work applies formal methods to verify the safety-critical firmware of commercial neural implants. This is a significant gap given the life-safety consequences of firmware bugs or malicious modifications.

- **Benchmark datasets for neural signal security:** No standardized datasets exist for evaluating attack detection, integrity verification, or authentication methods on neural signals. Researchers use ad hoc datasets with different recording systems, signal qualities, and task paradigms, making results incomparable. **VIREON aims to fill this gap through its benchmarking framework.**

- **Reproducible security assessment methodologies:** Existing security assessments are one-off academic exercises. No standardized, reproducible methodology exists for evaluating the security of neurotechnology systems. Each research group uses different tools, different threat models, and different evaluation criteria. **VIREON's validation framework directly addresses this gap.**

- **Closed-loop system security:** Most research focuses on open-loop recording or stimulation. Closed-loop systems (where recording drives stimulation in real-time) create new attack classes — data injection attacks that exploit the feedback loop, oscillation attacks that destabilize the control system, and covert channel attacks that use the stimulation-recording loop as a communication channel.

- **Regulatory science for neurotechnology security:** No regulatory framework specifically addresses the unique properties of neural data and neural implants. Current FDA guidance (Content of Premarket Submissions for Management of Cybersecurity in Medical Devices) is generic across all medical devices and does not address the specific risks of neurotechnology.

- **Long-term neural implant security:** No research addresses the security implications of devices implanted for decades. How do cryptographic keys degrade over time? How do firmware vulnerabilities accumulate? What is the attack surface evolution over a 15-year device lifetime?