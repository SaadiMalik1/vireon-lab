# VIREON: Virtual Laboratory for BCI Security

> [!CAUTION]
> **Research/Education Testbed — Simulated Security**
> VIREON is for research and educational purposes only. It uses **simulated security** and mock cryptographic operations. It is **not** for clinical, diagnostic, or production use.
[![CI](https://github.com/SaadiMalik1/Vireon/actions/workflows/ci.yml/badge.svg)](https://github.com/SaadiMalik1/Vireon/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
**Audience**: Security Researchers, Academic Researchers, Developers

## What is VIREON?
VIREON is an open-source research platform for simulating, validating, and evaluating the security of implantable neurotechnology.

It provides a complete **cyber-physical kill chain evaluator** that allows researchers to model the entire attacker lifecycle—from reconnaissance and initial access to physical signal manipulation—across different neurotechnology ecosystems (DBS, VNS, Cochlear, BCI).

## Core Features
- **Attack Lifecycle Engine**: Model threat actors from passive observers (L0) up to supply-chain root compromises (L6) across 7 distinct attack stages.
- **Structured Threat Models**: Declarative YAML models defining assets, boundaries, and assumptions for standard neurotech ecosystems.
- **Intrusion Detection & ZTA**: Test and validate neuro-IDS heuristics and Zero-Trust architectures dynamically.
- **Capture-The-Flag (CTF)**: Built-in interactive neurosecurity challenges to teach and evaluate threat-modeling concepts.
- **Web Dashboard**: Real-time telemetry monitoring through a Streamlit UI.
- **Compliance Tooling**: Generate FDA 524B-compliant SBOMs, compliance reports, and audit SPDF practices automatically.

## Component Status Matrix
| Component | Status | Description |
|-----------|--------|-------------|
| **OpenBCI Cyton Emulator** | **Working** | Real PTY, accurate framing at correct scale. |
| **Fuzzer** | **Working** | Mutation fuzzer with a real accept/reject oracle. |
| **Plugin Registry** | **Working** | Thread-safe entry-point discovery. |
| **Closed-Loop DBS** | **Working** | Emulated STN LFP and stimulation modulation. |
| **Cryptography** | **SIMULATED** | Crypto primitives are simulated (XOR) for modeling; not mathematically secure. |
| **Compliance Evidence** | **SIMULATED** | FDA 524B outputs are generated from simulated controls. |
| **Physics / Biology** | **SIMULATED** | Generic algorithms used for educational threat modeling, not validated for clinical accuracy. |

## Who Should Use It?
- **Academic Researchers**: To model the physiological impact of adversarial stimuli without human subjects.
- **Security Researchers**: To develop and validate Intrusion Detection Systems (IDS) and Zero-Trust Architectures (ZTA) for medical implants.
- **Medical Device Engineers**: To test bounded execution, battery constraints, and anti-rollback safeguards on simulated firmware.

## Scientific Disclaimer
> [!WARNING]
> **Not Medically Validated**: The physical and physiological equations modeled by VIREON (e.g., thermal tissue limits, generic EEG generation) are approximations built for cybersecurity threat modeling. They have **not** been validated for clinical accuracy and must not be used to make medical decisions.

> [!CAUTION]
> **Simulated Cryptography**: No real cryptographic operations (like AES-GCM or TLS) are performed by VIREON. All cryptographic functions are entirely simulated (e.g., XOR patterns) for the purpose of threat modeling. Do not rely on VIREON's cryptographic primitives for mathematical security.

---

## Installation & Prerequisites

It is highly recommended to use a virtual environment. The project requires **Python 3.10+** and **Rust 1.85+**.

```bash
git clone https://github.com/SaadiMalik1/Vireon.git
cd Vireon
python3 -m venv .venv
source .venv/bin/activate

# Install the project and all optional dependencies (including UI and Docs)
pip install -e ".[all]"
```

*Note: For detailed instructions regarding Rust toolchains for the NeuroDSL compiler, see the [Installation Guide](INSTALL.md).*

---

## Quick Start & CLI Workflow

VIREON provides a powerful, unified CLI (`vireon`) for all core functions.

### 1. Headless Simulation
Run a 10-second headless simulation with an active noise attack:
```bash
vireon run --duration 10.0 --attack noise
```

### 2. Interactive Web Dashboard
Launch the Streamlit UI to monitor physical states, IDS alerts, and active attacks in real time:
```bash
vireon ui --port 7777
```

### 3. Capture-The-Flag (CTF) Mode
List and play interactive neurosecurity challenges:
```bash
# View available challenges
vireon ctf list

# Start a specific challenge (e.g., ctf-001)
vireon ctf start ctf-001
```

### 4. Compliance & Audit Tools
Generate FDA 524B compliance documentation:
```bash
vireon sbom -o output/sbom.json
vireon compliance-report -o output/compliance.json
vireon audit-spdf
```

### 5. Fuzzing & Diagnostics
Run protocol fuzzing or view loaded plugins:
```bash
vireon info
vireon fuzz --iterations 5000 --protocol vireon
```

---

## Project Structure
```text
vireon/
├── attack_chain/   # 7-stage cyber kill chain lifecycle models
├── core/           # Coordinator, Engine, ZTA, IDS, Digital Twin
├── ctf/            # Capture-the-Flag challenge engine & content
├── dashboard/      # Streamlit interactive Web UI
├── plugins/        # Firmware Emulators, BLE clients, Datasets
├── tests/          # Pytest validation scripts
├── neuro_dsl/      # Embedded Rust DSL Compiler
└── __main__.py     # Unified CLI entry point
threat_models/      # Declarative YAML ecosystem threat models
docs/               # Technical, scientific, and API documentation
```

## Documentation Links
- [Full Documentation Index](docs/index.md)
- [System Architecture](docs/architecture.md)
- [Threat Modeling & Security](docs/threat-model/README.md)
- [API Reference](docs/api.md)
- [Plugin Development Guide](docs/plugin-development.md)

---

## Contributing
We welcome contributions from researchers and engineers! Please read our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md).

## Support
For help, please refer to [SUPPORT.md](SUPPORT.md).

## License
VIREON is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.
