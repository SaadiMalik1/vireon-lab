# NeuroShield: Virtual Laboratory for BCI Security

[![CI](https://github.com/SaadiMalik1/neurosheild/actions/workflows/ci.yml/badge.svg)](https://github.com/SaadiMalik1/neurosheild/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-80%25-green.svg)]()

**Audience**: Security Researchers, Academic Researchers, Developers

## What is NeuroShield?
NeuroShield is an extensible cyber-physical simulation framework for research, validation, and security assessment of neurotechnology systems, including Implantable Brain-Computer Interfaces (BCI), Deep Brain Stimulators (DBS), and Vagus Nerve Stimulators (VNS). It simulates the complex interaction between malicious firmware/RF commands, device physics (battery, thermal constraints), and physiological tissue responses (EEG traces).

## Why does it exist?
As neurotechnology transitions from clinical labs to commercial availability, the attack surface for "neural ransomware", stimulation leakage, and cognitive state inference expands. NeuroShield exists to model these threats safely in a digital environment before they manifest in clinical reality, adhering mathematically and ethically to the OSI of Mind and Quantified Interconnection Framework (QIF).

## Who Should Use It?
- **Academic Researchers**: To model the physiological impact of adversarial stimuli without human subjects.
- **Security Researchers**: To develop and validate Intrusion Detection Systems (IDS) and Zero-Trust Architectures (ZTA) for medical implants.
- **Medical Device Engineers**: To test bounded execution, battery constraints, and anti-rollback safeguards on simulated firmware.

## Who Should NOT Use It?
- **Clinicians/Patients**: NeuroShield is a simulation tool. It is not diagnostic medical software and cannot be used to tune actual patient therapy.
- **General Hobbyists**: Without a foundational understanding of cyber-physical systems or neuro-engineering, the telemetry output may be misinterpreted.

## Current Maturity Level
NeuroShield is currently a **Research Prototype**. The core simulation loop is stable, but APIs and plugin architectures are subject to rapid, breaking changes.

## Scientific Disclaimer
> [!WARNING]
> **Not Medically Validated**: The physical and physiological equations modeled by NeuroShield (e.g., thermal tissue limits, generic EEG generation) are approximations built for cybersecurity threat modeling. They have **not** been validated for clinical accuracy and must not be used to make medical decisions.

---

## Features

### Implemented
- **Digital Twin Physics Engine**: Simulates battery drain, thermal limits, and electrode impedance.
- **Coordinator & Event Bus**: Orchestrates real-time telemetry streaming (LSL) and attack injection.
- **Zero-Trust Architecture (ZTA)**: Context-aware authorization engine that degrades trust during active attacks.
- **Onboard NeuroIDS**: ML-based intrusion detection with graceful degradation (Deep Autoencoder -> Linear).
- **OTA Rollback Emulation**: Anti-rollback verification of firmware versions using simulated efuses.
- **Biometric Gating**: Verifies simulated neural signatures (e.g., N400 ERP) before executing high-risk commands.

### Experimental
- **Runemate DSL**: Embedded Rust compiler for executing bounded, memory-safe clinical therapy scripts.
- **End-to-End Encryption (E2EE)**: Symmetric key derivation for telemetry streams.

### Future Work
- **Swarm Interference Emulator**: Cross-implant attack simulations (e.g., Pacemaker pivoting to DBS).
- **Hardware-in-the-Loop (HIL)**: Integration with physical OpenBCI boards.

---

## Architecture Overview
NeuroShield operates on a tightly-coupled, three-pillar architecture:
1. **The Digital Twin**: Models the physical state (battery, temperature) and clinical state (EEG, cognitive load).
2. **The Emulator**: Models the firmware state, OTA update verification, and memory safety.
3. **The Coordinator**: The central orchestrator that applies ZTA policies, injects attacks (e.g., Firmware Rollback, MTU Abuse), and emits telemetry.

*See [docs/architecture.md](docs/architecture.md) for detailed flow diagrams.*

---

## Installation

### Prerequisites
- Python 3.10+
- Cargo/Rust (required for Runemate compilation)

```bash
git clone https://github.com/SaadiMalik1/neurosheild.git
cd neurosheild
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Quick Start & Example Workflow

**1. Run a 10-second headless simulation with an active noise attack:**
```bash
python3 -m neuroshield run --duration 10.0 --attack noise
```

**2. Expected Workflow:**
- The Coordinator initializes the Twin and IDS.
- The simulation begins generating baseline EEG telemetry.
- At t=5.0s, the "noise" attack injects targeted high-frequency interference.
- The ZTA Policy Engine detects anomalous context and degrades trust.
- Telemetry egress is halted; an alert is generated.
- PDF diagnostic reports are generated in the root directory.

**3. Launch the Web Dashboard:**
```bash
python3 -m neuroshield ui --port 7777
```

---

## Project Structure
```text
neuroshield/
├── core/           # Coordinator, Engine, ZTA, IDS, Digital Twin
├── plugins/        # Firmware Emulators, BLE clients, Extensible datasets
├── tests/          # Pytest validation and manual verification scripts
├── runemate/       # Embedded Rust DSL Compiler
├── docs/           # Technical, scientific, and API documentation
└── main.py         # CLI entry point
```

## Plugin System
NeuroShield uses an extensible plugin architecture. New medical devices, attack vectors, or threat intelligence feeds can be added by implementing the base classes in `neuroshield/plugins/`.

---

## Roadmap
See [ROADMAP.md](ROADMAP.md) (coming in Milestone 2) for our quarterly objectives.

## Known Limitations
- EEG data is currently procedurally generated (synthetic); integrating real pre-recorded datasets is an experimental feature.
- Deep Autoencoder inference adds significant latency (~50ms) to the event loop; not suitable for hard-real-time physical deployments.

## Documentation Links
- [Full Documentation Index](docs/index.md)
- [System Architecture](docs/architecture.md)
- [Security & Threats](docs/security_and_threats.md)
- [API Reference](docs/api.md)

---

## Contributing
We welcome contributions from researchers and engineers! Please read our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md).

## Support
For help, please refer to [SUPPORT.md](SUPPORT.md).

## License
NeuroShield is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation
If you use NeuroShield in your research, please cite it using the provided [CITATION.cff](CITATION.cff) file.

## Acknowledgments
We drew heavy inspiration from the [qinnovates/neurosecurity](https://github.com/qinnovates/neurosecurity) repository and their Quantified Interconnection Framework (QIF).
