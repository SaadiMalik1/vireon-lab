# Deep Brain Stimulation (DBS): The Active Attack Surface

Unlike EEG which merely records data, Deep Brain Stimulation (DBS) is an active, implantable Cyber-Physical System (CPS). An Implantable Pulse Generator (IPG) sits in the chest, delivering precisely calibrated electrical waveforms via subcutaneous leads to targeted brain regions (e.g., the Subthalamic Nucleus or Globus Pallidus). Because DBS actively alters neural computation, it represents a critical life-safety attack surface.

## 1. Engineering the Therapy (Waveform Parameters)

DBS therapy is not a continuous current; it is a rapid series of discrete electrical pulses. The IPG firmware manages several key parameters, each representing an axis of vulnerability:

- **Amplitude (Voltage or Current)**: The strength of the pulse. Higher amplitudes recruit a larger volume of tissue (Volume of Tissue Activated, VTA).
  - *Vulnerability*: Forcing amplitude beyond safety thresholds ($>10\text{V}$ or equivalent current) can cause localized tissue necrosis or unwanted recruitment of adjacent neural tracts (causing severe side effects like muscle tetany).
- **Pulse Width**: The duration of a single pulse (typically $60-120\text{\mu s}$).
  - *Vulnerability*: Longer pulse widths increase the total injected charge per phase. Exceeding the Shannon Equation limits for safe charge density ($\mu C/cm^2$) causes irreversible electroporation of cell membranes.
- **Frequency**: The rate of pulses (typically $130-185\text{Hz}$ for Parkinson's).
  - *Vulnerability*: Altering frequency disrupts the intended desynchronization of pathological neural oscillations. A malicious drop to $20\text{Hz}$ might worsen tremors, while spiking to $>250\text{Hz}$ rapidly depletes neurotransmitters.

*Relevance to VIREON*: The `vireon` physics engine mathematically models these three variables. Our `NeuroethicsGuardrails` module constantly integrates the total charge delivered over time, asserting hard limits to prevent simulated tissue damage.

## 2. Open-Loop vs. Closed-Loop Architectures

Modern DBS is transitioning from open-loop (continuous stimulation regardless of patient state) to closed-loop (Adaptive DBS / aDBS).

- **Adaptive DBS**: The implant records Local Field Potentials (LFPs) directly from the stimulating electrode, processes biomarkers (like Beta-band oscillation power), and adjusts the stimulation amplitude in real-time.
- **The Closed-Loop Vulnerability**: The feedback loop introduces a massive logical attack surface. If an adversary injects electromagnetic noise (EMI) that mimics a high Beta-band signal, the aDBS algorithm may mistakenly ramp up stimulation to maximum amplitude. This is a semantic "sensor spoofing" attack, exploiting the algorithm's trust in its own leads.

## 3. Physical & Firmware Threat Vectors

- **Battery Drain (Biological DoS)**: Constantly commanding the IPG to deliver maximum allowed amplitude at maximum frequency forces premature battery depletion. For non-rechargeable implants, this necessitates emergency chest surgery.
- **Impedance Spikes**: Normal tissue-electrode impedance is $500-1500 \text{ \Omega}$. A sudden spike ($>3000 \text{ \Omega}$) usually indicates a broken lead wire. However, an attacker manipulating the IPG firmware could artificially report high impedance to trigger an automatic therapy shutdown, denying service.
- **Over-The-Air (OTA) Updates**: Because the IPG must communicate with external clinical programmers (via BLE or MICS bands), unauthenticated OTA firmware updates represent the highest-severity risk, allowing complete hijack of the pulse parameters.

In VIREON, the `NeuroDSL` (formerly Runemate) compiler is used to safely script these therapies, ensuring that even if an attacker compromises the high-level logic, the compiled bytecode strictly adheres to the hardware's electrochemical constraints.
