# qTARA Threat Registry

**Audience**: Security Researchers, Academic Researchers

VIREON integrates with the **qTARA** (Threat Assessment & Remediation Analysis) registry. qTARA provides standardized codes for cataloging cyber-physical neurosecurity threats. This allows researchers to communicate complex physiological attacks using standardized taxonomy.

## Implemented qTARA Mappings

Below are the currently supported Threat Codes that the VIREON Intrusion Detection System (IDS) and ZTA engines can identify and alert on.

### QIF-T0001: Stimulation Parameter Tampering
- **Description**: An attacker modifies the amplitude, frequency, or pulse width of a stimulation therapy beyond safe therapeutic thresholds.
- **Simulation Event**: Detected when the `SimulatorEngine` receives a payload altering baseline parameters dynamically.
- **Physiological Impact**: Tissue heating, localized pain, disruption of targeted therapy.

### QIF-T0002: Telemetry Interception (State Inference)
- **Description**: An attacker passively sniffs the BLE or LSL data streams to infer the patient's broad physiological or cognitive state.
- **Simulation Event**: Logged when the simulated RF link lacks E2EE and is exposed to the local network loopback.
- **Physiological Impact**: Privacy violation.

### QIF-T0003: Firmware Rollback Attack
- **Description**: An attacker forces the device to downgrade to a vulnerable, previously signed firmware version by bypassing eFuse checks.
- **Simulation Event**: Evaluated during the `simulate_firmware_update` cycle within the `Coordinator`.
- **Physiological Impact**: Re-opens previously patched vulnerabilities (e.g., re-enabling QIF-T0001).

### QIF-T0004: Resource Exhaustion (Battery/Thermal)
- **Description**: An attacker keeps the implant CPU or radio active continuously, draining the primary battery cell and generating excess heat.
- **Simulation Event**: Triggered by the `MTUAbuseAttack` plugin or infinite loop execution.
- **Physiological Impact**: Device shutdown (Denial of Therapy), thermal tissue damage.
