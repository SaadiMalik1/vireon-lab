# NeuroShield: Virtual Laboratory for BCI Security

[![CI](https://github.com/SaadiMalik1/neurosheild/actions/workflows/ci.yml/badge.svg)](https://github.com/SaadiMalik1/neurosheild/actions/workflows/ci.yml)

**Audience**: Security Researchers, Academic Researchers, Developers

## What is NeuroShield?
NeuroShield is an extensible cyber-physical simulation framework for research, validation, and security assessment of neurotechnology systems, including Implantable Brain-Computer Interfaces (BCI), Deep Brain Stimulators (DBS), and Vagus Nerve Stimulators (VNS). It simulates the complex interaction between malicious firmware/RF commands, device physics (battery, thermal constraints), and physiological tissue responses (EEG traces).

## Why does it exist?
As neurotechnology transitions from clinical labs to commercial availability, the attack surface expands. NeuroShield exists to model threats—such as unauthorized stimulation, telemetry manipulation, device denial-of-service, state inference, firmware compromise, and wireless protocol abuse—safely in a digital environment before they manifest in clinical reality. 

NeuroShield is influenced by the principles proposed in the OSI of Mind and Quantified Interconnection Framework (QIF), which are currently under active development.

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

## Architecture Overview

```text
       CLI / Scripts
             │
             ▼
      [ Coordinator ] ──────────────┐
             │                      │
             ▼                      │
     [ Plugin Manager ]             │
             │                      │
             ▼                      ▼
   [ Simulation Engine ] ◄──── [ Attack Framework ]
             │
             ▼
     [ Digital Twin ]
      ├─ Physics (Thermal/Battery)
      ├─ Firmware (OTA/Execution)
      └─ Signals (EEG/Biometrics)
             │
             ▼
       [ Telemetry ]
      (LSL / WebSockets)
             │
             ▼
         [ Reports ]
```

---

## Core Components

### Implemented
- **Digital Twin**: Models the physical state (battery, temperature) and clinical state (EEG, cognitive load) of the simulated patient.
- **Simulation Engine**: A tick-based execution loop that drives the physics models and synchronizes component states.
- **Coordinator**: The central orchestrator that applies ZTA policies, manages the event bus, and controls the simulation lifecycle.
- **Plugin System**: An event-driven architecture allowing researchers to inject custom device models, telemetry outputs, or attack vectors without modifying the core engine.
- **Attack Framework**: A registry of simulated adversarial behaviors, such as OTA Rollback manipulation and BLE MTU abuse.
- **Reporting**: Automated generation of HTML and PDF diagnostic reports detailing anomalies and physiological state changes post-simulation.
- **Zero-Trust Architecture (ZTA)**: A context-aware authorization engine that dynamically degrades system trust during active attacks.
- **Prototype Anomaly Detection Module (NeuroIDS)**: An experimental machine learning module that falls back gracefully from a PyTorch-based Deep Autoencoder to a Numpy-based Linear Autoencoder.
- **CLI**: The command-line interface for headless, reproducible simulation execution.
- **Dashboard**: A real-time Streamlit diagnostic web interface for visualizing EEG traces and physical metrics.

### Experimental
- **Runemate DSL**: An embedded Rust compiler for executing bounded, memory-safe clinical therapy scripts.
- **E2EE**: Symmetric key derivation and encryption layer for securing simulated telemetry streams.

### Future Work
- **Swarm Interference Emulator**: Cross-implant attack simulations (e.g., Pacemaker pivoting to DBS).
- **Hardware-in-the-Loop (HIL)**: Integration with physical OpenBCI boards.

---

## Installation & Prerequisites
See the [Installation Guide](INSTALL.md) for detailed instructions on Python virtual environments and Rust toolchains.

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

## Documentation Links
- [Full Documentation Index](docs/index.md)
- [System Architecture](docs/architecture.md)
- [Threat Modeling & Security](docs/threat-model/README.md)
- [API Reference](docs/api.md)
- [Plugin Development Guide](docs/plugin-development.md)
- [Frequently Asked Questions](docs/FAQ.md)

---

## Contributing
We welcome contributions from researchers and engineers! Please read our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md).

## Support
For help, please refer to [SUPPORT.md](SUPPORT.md).

## License
NeuroShield is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation
If you use NeuroShield in your research, please cite it using the provided [CITATION.cff](CITATION.cff) file.
