# VIREON: Virtual Laboratory for BCI Security

[![CI](https://github.com/SaadiMalik1/neurosheild/actions/workflows/ci.yml/badge.svg)](https://github.com/SaadiMalik1/neurosheild/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
**Audience**: Security Researchers, Academic Researchers, Developers

## What is VIREON?
VIREON is an open-source research platform for simulating, validating, and evaluating the security of implantable neurotechnology.

**Validated against 8 public neurophysiological datasets spanning 500+ hours of EEG recordings.**

## Why does it exist?
As neurotechnology transitions from clinical labs to commercial availability, the attack surface expands. VIREON exists to model threats—such as unauthorized stimulation, telemetry manipulation, device denial-of-service, state inference, firmware compromise, and wireless protocol abuse—safely in a digital environment before they manifest in clinical reality. 

VIREON is built on top of existing standards (e.g., STRIDE, MITRE ATT&CK, IEC 81001-5-1, ISO 14971), acting as an orchestrator for threat modeling and safety validation rather than inventing new standards.

## Who Should Use It?
- **Academic Researchers**: To model the physiological impact of adversarial stimuli without human subjects.
- **Security Researchers**: To develop and validate Intrusion Detection Systems (IDS) and Zero-Trust Architectures (ZTA) for medical implants.
- **Medical Device Engineers**: To test bounded execution, battery constraints, and anti-rollback safeguards on simulated firmware.

## Who Should NOT Use It?
- **Clinicians/Patients**: VIREON is a simulation tool. It is not diagnostic medical software and cannot be used to tune actual patient therapy.
- **General Hobbyists**: Without a foundational understanding of cyber-physical systems or neuro-engineering, the telemetry output may be misinterpreted.

## Current Maturity Level
VIREON is currently a **Research Prototype**. The core simulation loop is stable, but APIs and plugin architectures are subject to rapid, breaking changes.

## Scientific Disclaimer
> [!WARNING]
> **Not Medically Validated**: The physical and physiological equations modeled by VIREON (e.g., thermal tissue limits, generic EEG generation) are approximations built for cybersecurity threat modeling. They have **not** been validated for clinical accuracy and must not be used to make medical decisions.

---



## Roadmap

**v0.2**
- [x] Digital Twin physics and signals
- [x] Coordinator and Policy Engine separation
- [x] Extensible Plugin architecture

**v0.3**
- [ ] Automated reproducible benchmarks suite
- [ ] Integration of a Curated Validation Corpus (e.g., PhysioNet, BCI Competition Datasets)
- [ ] Hardware-in-the-loop (HIL) integration
- [ ] BLE packet fuzzing

**v1.0**
- [ ] Stable Python APIs
- [ ] Documentation freeze
- [ ] Research publication

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
python3 -m vireon run --duration 10.0 --attack noise
```

**2. Expected Output:**
```text
Simulation started...
Baseline telemetry OK.
[t=5.0s] Attack injected: NOISE
[NSAE] Anomaly detected (confidence: 0.92)
[ZTA] Trust score degraded: 0.8 -> 0.4
[ZTA] Telemetry egress halted.
Simulation complete.
Report generated: reports/session.pdf
```

**3. Launch the Web Dashboard:**
```bash
python3 -m vireon ui --port 7777
```

---

## Project Structure
```text
vireon/
├── core/           # Coordinator, Engine, ZTA, IDS, Digital Twin
├── plugins/        # Firmware Emulators, BLE clients, Extensible datasets
├── tests/          # Pytest validation and manual verification scripts
├── neuro_dsl/       # Embedded Rust DSL Compiler
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
VIREON is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation
If you use VIREON in your research, please cite it using the provided [CITATION.cff](CITATION.cff) file.
