# VIREON Standards Mapping Registry

**Audience**: Security Researchers, Academic Researchers

VIREON integrates directly with established cybersecurity frameworks (STRIDE, MITRE CWE, IEC 62304). This provides standardized mapping for cataloging cyber-physical neurosecurity threats. This allows researchers to communicate complex physiological attacks using standardized cybersecurity taxonomy rather than proprietary frameworks.

## Implemented Threat Mappings

Below are the currently supported threat categories that the VIREON Intrusion Detection System (IDS) and ZTA engines can identify and alert on, mapped against standard frameworks.

### ATTACK-001: Stimulation Parameter Tampering (STRIDE: Tampering)
- **Description**: An attacker modifies the amplitude, frequency, or pulse width of a stimulation therapy beyond safe therapeutic thresholds.
- **Simulation Event**: Detected when the `SimulatorEngine` receives a payload altering baseline parameters dynamically.
- **Physiological Impact**: Tissue heating, localized pain, disruption of targeted therapy.

### ATTACK-002: Telemetry Interception / State Inference (STRIDE: Information Disclosure)
- **Description**: An attacker passively sniffs the BLE or LSL data streams to infer the patient's broad physiological or cognitive state.
- **Simulation Event**: Logged when the simulated RF link lacks E2EE and is exposed to the local network loopback.
- **Physiological Impact**: Privacy violation.

### ATTACK-003: Firmware Rollback Attack (STRIDE: Elevation of Privilege)
- **Description**: An attacker forces the device to downgrade to a vulnerable, previously signed firmware version by bypassing eFuse checks.
- **Simulation Event**: Evaluated during the `simulate_firmware_update` cycle within the `Coordinator`.
### ATTACK-004: Resource Exhaustion / Battery Drain (STRIDE: Denial of Service)
- **Description**: An attacker keeps the implant CPU or radio active continuously, draining the primary battery cell and generating excess heat.
- **Simulation Event**: Triggered by the `MTUAbuseAttack` plugin or infinite loop execution.
- **Physiological Impact**: Device shutdown (Denial of Therapy), thermal tissue damage.
