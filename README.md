# vireon-lab — Educational Platform

**Interactive Neurosecurity Simulation & Educational Dashboard**

`vireon-lab` is an educational platform for students, researchers, and educators learning neurosecurity. Built on top of the **[Vireon](https://github.com/SaadiMalik1/Vireon)** Pre-Alpha research runtime, it provides an interactive Streamlit browser dashboard, attack scenario visualizers, threat atlas reference data, and hands-on tutorials.

---

## 1. Current State & Included Modules

- **Interactive Dashboard**: Streamlit browser UI (`vireon_lab/dashboard/app.py`) for demonstrating BCI attack scenarios (adversarial ML, signal spoofing, DBS closed-loop manipulation).
- **Emulators**: Software emulators for OpenBCI Cyton, PiEEG SPI interface, BLE GATT, and DBS LFP generators (`tests/` matrix verified).
- **Integrated Knowledge Base**: 5 complete Neurosecurity curriculum modules (`knowledge/lessons/`):
  - **NL-001**: Neural Signals & The Neurosecurity Problem Space (Foundations, Deep Analysis, Synthesis, CTF Challenges, References).
  - **NL-002**: Neural Signal Processing for Security Analysts (Filtering, Feature Extraction, Failure Modes, Challenges, References).
  - **NL-003**: Neurostimulator Firmware Architecture & Security (Cortex-M Execution, DSP Engines, STRIDE Analysis, Challenges, References).
  - **NL-004**: Wireless Protocol Security for Neurostimulators (MICS/BLE Telemetry, Protocol Reverse Engineering, Challenges, References).
  - **NL-005**: Closed-Loop System Security for Neurostimulators (Sensor Spoofing, Delay Injection, Benchmarks, Challenges, References).
- **Hands-on Labs & Simulators**: Interactive Python simulation engines (`knowledge/simulators/`) for signal generation, DSP filtering, firmware reverse engineering, protocol attacks, and closed-loop control.
- **Threat Modeling & Data Benchmarks**: STRIDE threat modeling lab templates (`knowledge/labs/`) and empirical benchmark datasets/session dumps (`knowledge/data/`).
- **Test Suite Verification:** 59 Python tests passed (`pytest`).


---

## 2. Quick Start

```bash
# Clone the repository
git clone https://github.com/SaadiMalik1/vireon-lab.git
cd vireon-lab

# Install dependencies in editable mode
.venv/bin/pip install --no-deps -e .

# Launch the interactive Streamlit dashboard
.venv/bin/streamlit run vireon_lab/dashboard/app.py
```

---

## 3. Verification & Testing

```bash
.venv/bin/pytest       # Runs pytest suite (59 passed)
```

---

## 4. Architecture & Dependencies

`vireon-lab` depends on `vireon` as its underlying simulation core. Core orchestrator logic, deterministic clocks, and capability engines reside in the **[Vireon](https://github.com/SaadiMalik1/Vireon)** runtime repository.
