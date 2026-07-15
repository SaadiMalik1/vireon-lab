# Threat Modeling

This directory (and the adjacent `threat_models/` directory in the root) contains the formal threat model for the VIREON simulation environment. We strictly define the boundaries of our simulations to ensure scientific and engineering rigor, avoiding theoretical scenarios that lack physiological or physical backing.

## Attack Lifecycle (Kill Chain)

VIREON models the entire attack lifecycle against neurotechnology systems, rather than just assuming an attacker already has a shell. This lifecycle allows researchers to simulate and defend against attacks at any stage:

```text
Reconnaissance
        ↓
Device Discovery
        ↓
Communication Analysis
        ↓
Protocol Reverse Engineering
        ↓
Initial Access
        ↓
Privilege Escalation
        ↓
Persistence
        ↓
Command & Control
        ↓
Safety-Critical Actions
        ↓
Detection & Response
        ↓
Recovery
```

## Attacker Capability Levels

Instead of assuming a shell, VIREON defines explicit attacker capability levels. Simulations configure these capabilities to determine whether an attacker can bypass specific boundaries (e.g., body-area networks vs. cloud infrastructure).

| Level | Attacker Capability | Example |
| :---: | :--- | :--- |
| **L0** | **Passive Observer** | Eavesdrops on unencrypted BLE telemetry but cannot inject traffic. |
| **L1** | **Local RF Manipulator** | Executes replay or jamming attacks over the air against the neurostimulator. |
| **L2** | **Companion App Compromise** | Has logical control over the patient's smartphone or intermediary hub device. |
| **L3** | **Protocol Exploiter** | Discovers and exploits vulnerabilities in the communication protocol (e.g., GATT abuse, unauthenticated pairing). |
| **L4** | **Cloud/API Compromise** | Modifies synchronization parameters, OTA firmware blobs, or clinical configurations hosted remotely. |
| **L5** | **Firmware Execution** | Achieves arbitrary code execution directly on the IPG (Implantable Pulse Generator) via RCE or malicious OTA update. |
| **L6** | **Supply Chain Root** | Alters bootloaders, hardware design, or clinical programming units prior to implantation or provisioning. |

## Declarative Ecosystem Threat Models

We use YAML-based declarative threat models to map specific neurotechnology ecosystems. Located in the root `threat_models/` directory, these files define assets, boundaries, and capability requirements. Current default ecosystems include:
- `dbs.yaml` (Deep Brain Stimulation)
- `vns.yaml` (Vagus Nerve Stimulation)
- `cochlear.yaml` (Cochlear Implants)
- `bci.yaml` (Brain-Computer Interfaces)

## Legacy Documents

1. **[Assumptions & Trust Boundaries](assumptions.md)**: Defines foundational epistemic boundaries and valid attack conditions.
2. **[Attack Surface](attack-surface.md)**: A detailed mapping of the legacy vectors (e.g., Firmware OTA interface, BLE GATT Server).
3. **[Standards Mapping Registry](../core/data/standards_mapping.json)**: An index mapping validation profiles to STRIDE, MITRE ATT&CK, CWE, and ISO 14971.
