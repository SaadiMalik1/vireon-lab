# vireon-lab — Educational Platform

**Interactive Neurosecurity Simulation & Educational Dashboard**

`vireon-lab` is an educational platform for students, researchers, and educators learning neurosecurity. Built on top of the **[Vireon](https://github.com/SaadiMalik1/Vireon)** production runtime, it provides an interactive Streamlit browser dashboard, attack scenario visualizers, threat atlas reference data, and step-by-step tutorials.

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/SaadiMalik1/vireon-lab.git
cd vireon-lab

# Install dependencies in editable mode
make install

# Launch the interactive Streamlit dashboard
make demo
```

---

## What vireon-lab Contains

- **Dashboard**: Interactive browser UI for BCI attack scenarios (adversarial ML, signal spoofing, DBS closed-loop manipulation).
- **Emulators**: Reference hardware and protocol emulators (OpenBCI Cyton, PiEEG, BLE GATT, DBS LFP).
- **Knowledge Base**: Curated reference materials on brain region mappings, threat models, and standards (ISO 14971, FDA cybersecurity guidance).
- **Tutorials**: Hands-on guides for running simulations and analyzing neurosecurity risks.

---

## Verification & Testing

```bash
make test       # Runs pytest suite for emulators and scenarios
make lint       # Enforces code quality via ruff and mypy
```

---

## Dependency Mandate

`vireon-lab` depends on `vireon` as a core library package. All core simulation logic, scheduler engines, and state stores reside in the **[Vireon](https://github.com/SaadiMalik1/Vireon)** runtime repository.
