# Security Assumptions & Trust Boundaries

**Audience**: Security Researchers, Academic Researchers

## Trust Boundaries

To accurately model cyber-physical attacks on medical implants, VIREON establishes the following formal trust boundaries:

1. **The Patient (Trusted but Vulnerable)**
   - The physiological state of the patient (modeled by the Digital Twin) is considered trusted ground truth.
   - An attacker **cannot** directly overwrite the EEG variables via an API call. 
   - An attacker **can** influence the EEG indirectly by manipulating the implant's stimulation parameters.

2. **The Firmware (Untrusted)**
   - The simulated implant firmware operates in a hostile environment.
   - We assume a powerful attacker model where the attacker has achieved **Remote Code Execution (RCE)** on the implant's processor or has compromised the firmware update signing key (OTA Rollback).

3. **The RF Link (Untrusted)**
   - The Bluetooth Low Energy (BLE) link between the external controller and the implant is untrusted.
   - Attackers can inject, drop, or delay logical packets (e.g., MTU Abuse).

## Epistemic Limits (Scientific Bounding)

VIREON adheres to established industry standards regarding scientific validity. We explicitly refuse to simulate "sci-fi" attacks.

### In-Scope Attacks (Simulated)
- **Denial of Service (DoS)**: Draining the battery via continuous stimulation or flooding the BLE stack.
- **Unauthorized Stimulation**: Inducing unwanted physiological states (e.g., causing pain or disrupting therapy).
- **Tissue Heating**: Exceeding safe thermal limits by abusing the power amplifier.
- **Broad State Inference**: Deducing simple physiological states (e.g., Sleep/Wake cycles) from intercepted telemetry.

### Out-of-Scope Attacks (Rejected)
- **"Mind Reading"**: Extracting complex, plain-text semantic thoughts or passwords from motor-cortex EEG data. 
- **"Mind Control"**: Overriding a patient's complex behavioral choices.
