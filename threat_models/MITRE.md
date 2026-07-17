# MITRE ATT&CK Mapping for VIREON

This document maps the simulated attacks within the VIREON platform to the MITRE ATT&CK framework, distinguishing between threats against the simulated **Target Device** and threats against the **Simulation Platform** itself.

## 1. Simulation Platform Threats

These threats target the VIREON software, virtual machines, and plugins directly, aiming to compromise the researcher's host or invalidate the simulation.

### Initial Access
- **T1190 - Exploit Public-Facing Application:** Exploitation of the vulnerable Web Server plugin to gain code execution on the simulation host.
- **T1204 - User Execution:** Tricking a researcher into loading a malicious `.yaml` threat model that leverages YAML deserialization vulnerabilities.

### Execution
- **T1059 - Command and Scripting Interpreter:** NeuroDSL VM execution of malicious or unverified scripts that escape the VM to the host system.

### Defense Evasion
- **T1562 - Impair Defenses:** Disabling or tampering with the `core/detection.py` metrics to blind the simulation to active neurodevice attacks.

## 2. Simulated Target Device Threats

These threats target the virtual neurodevice running within the simulation, representing real-world ICS/medical device vulnerabilities.

### Initial Access
- **T1195 - Supply Chain Compromise:** Simulated via Malicious Firmware Update (OTA).

### Execution
- **T1203 - Exploitation for Client Execution:** Sending malformed neurostimulation payloads to trigger buffer overflows in the virtual `cortex_m_stub.py`.

### Persistence
- **T1542 - Pre-OS Boot:** Bootloader compromise via unsigned firmware. Mitigation implemented via Signature Verification.

### Privilege Escalation
- **T1068 - Exploitation for Privilege Escalation:** Accessing restricted memory regions via debugger interface.

### Evasion
- **T1140 - Deobfuscate/Decode Files or Information:** Replaying neural signals to bypass basic anomaly detection (simulated spoofing).

### Impact
- **T1495 - Firmware Corruption:** Overwriting critical memory regions in the digital twin.
- **T1499 - Endpoint Denial of Service:** Battery drain via high-frequency stimulation (Resource Exhaustion/Peukert's Law).
- **T1565 - Data Manipulation:** Tampering with stimulation parameters to induce tissue damage (Pennes Bioheat violation).

## Coverage and Gaps
The simulated attack scenarios (Insider, OTA Tampering, Battery Drain) are designed to cover multiple tactics across the MITRE ATT&CK lifecycle. By separating platform threats from simulated threats, we ensure researchers evaluate both the safety of the modeled device and the integrity of the VIREON testing environment.
