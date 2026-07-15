# Threat Modeling

This directory (and the adjacent `threat_models/` directory in the root) contains the formal threat model for the VIREON simulation environment. We strictly define the boundaries of our simulations to ensure scientific and engineering rigor, avoiding theoretical scenarios that lack physiological or physical backing.

## Attacker Capability System

Rather than running raw, disjointed exploit scripts, VIREON models an explicit progression of attacker capabilities (`L0` through `L6`). Simulations must configure the exact capabilities an attacker wields, determining whether they can bypass specific boundaries (e.g., body-area networks vs. cloud infrastructure).

- **L0 (Passive Observer)**: Eavesdrops on unencrypted telemetry but cannot inject traffic.
- **L1 (Local RF Manipulator)**: Executes replay or jamming attacks over the air.
- **L2 (Companion App Compromise)**: Has logical control over the patient's smartphone or intermediary device.
- **L3 (Protocol Exploiter)**: Discovers and exploits vulnerabilities in the communication protocol (e.g., GATT abuse).
- **L4 (Cloud/API Compromise)**: Modifies synchronization parameters or firmware blobs hosted remotely.
- **L5 (Firmware Execution)**: Achieves arbitrary code execution directly on the IPG via RCE.
- **L6 (Supply Chain Root)**: Alters bootloaders or hardware design prior to implantation.

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
