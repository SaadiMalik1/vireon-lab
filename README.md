# vireon-lab — Educational Platform

**Interactive Neurosecurity Simulation & Educational Dashboard**

`vireon-lab` is an educational platform for students, researchers, and educators learning neurosecurity. Built on top of the **[Vireon](https://github.com/SaadiMalik1/Vireon)** Pre-Alpha research runtime, it provides an interactive Streamlit browser dashboard, attack scenario visualizers, threat atlas reference data, and hands-on tutorials.

---

## 1. Current State & Included Modules

- **Interactive Dashboard**: Streamlit browser UI (`vireon_lab/dashboard/app.py`) for demonstrating BCI attack scenarios (adversarial ML, signal spoofing, DBS closed-loop manipulation).
- **Emulators**: Software emulators for OpenBCI Cyton, PiEEG SPI interface, BLE GATT, and DBS LFP generators (`tests/` matrix verified).
- **Knowledge Base**: Curated reference articles covering neuroscience basics (`knowledge/neuroscience/`), BLE communication protocols (`knowledge/protocols/`), and cybersecurity guidance (`knowledge/standards/`).
  - *Status Notice:* Regulatory subfolders (`knowledge/regulations/FDA`, `ISO`, `MDR`, `IEC`, `HIPAA`) are currently placeholder directories.
- **Tutorials & Modules**: Hands-on lesson modules (`Module/`) covering signal simulation, attack detection, and firmware reverse engineering exercises.
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
