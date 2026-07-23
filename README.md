# vireon-lab — Educational & Research Platform

**Interactive Neurosecurity Simulation, Physical Threat Mutator & Clinical Compliance Laboratory**

`vireon-lab` is an educational and research platform for students, security analysts, researchers, and medical device developers learning neurosecurity. Built on top of the **[Vireon](https://github.com/SaadiMalik1/Vireon)** Pre-Alpha research runtime, it provides an interactive Streamlit dashboard, modular signal engines, physical threat mutators, STIX 2.1 forensic exporters, and comprehensive curriculum modules.

---

## 1. Current State & Included Modules

- **Interactive Dashboard (`vireon_lab/dashboard/app.py`)**:
  - **Pure Obsidian Dark UI**: Clinical dark-mode interface with zero layout flickering.
  - **Phase-Continuous Telemetry Engine**: $O(1)$ ring-buffer streaming supporting selectable time windows from 2 seconds up to 5 minutes.
  - **Multi-Dataset Profiles**: Real-time switching across Synthetic Jansen-Rit, Real Clinical EEG (EDF/CSV), Motor Imagery BCI (PhysioNet), and Deep Brain Stimulation (DBS) Subthalamic LFP.
  - **6 Interactive Laboratories**: Live Neural Signals, Physical Signal Tampering, Closed-Loop DBS Control, Wireless & BLE Security, Adversarial ML Evasion, and Threat Matrix & Forensics.
- **Modular Signal Engine (`vireon_lab/engine/`)**:
  - **Neural Mass & AR Generators**: `JansenRitNeuralMassGenerator` and `ColoredNoiseARGenerator` for biologically realistic cortical dynamics.
  - **Physiological Artifact Injectors**: `EyeBlinkArtifact`, `EMGBurstArtifact`, `ECGLeakageArtifact`, and `ElectrodeMotionArtifact`.
  - **Physical Threat Mutators**: `GaussianNoiseAttack`, `DCOffsetDriftAttack`, `DoSGroundingAttack`, `SessionReplayAttack`, and `DBSPulseOverrideAttack`.
  - **Deterministic Scheduler**: `EventScheduler` for reproducible timeline simulations and experiment metadata export.
  - **$O(1)$ Circular Buffer**: `CircularBuffer` for high-throughput memory-efficient streaming without `np.roll()` memory copies.
- **Forensic & Compliance Exporter (`vireon_lab/dashboard/forensic_exporter.py`)**:
  - Automated **STIX 2.1 JSON Threat Bundle** generator.
  - **ISO 14971 & CWE Executive HTML Audit Report** generator.
- **Integrated Knowledge Base**: 5 complete Neurosecurity curriculum modules (`knowledge/lessons/`):
  - **NL-001**: Neural Signals & The Neurosecurity Problem Space.
  - **NL-002**: Neural Signal Processing for Security Analysts.
  - **NL-003**: Neurostimulator Firmware Architecture & Security.
  - **NL-004**: Wireless Protocol Security for Neurostimulators.
  - **NL-005**: Closed-Loop System Security for Neurostimulators.
- **Emulators & Hardware Bridges**: Software emulators for OpenBCI Cyton, PiEEG SPI interface, BLE GATT, and DBS LFP generators (`vireon_lab/providers/`).

---

## 2. Quick Start & Installation

### Prerequisites
- Python 3.10, 3.11, or 3.12

```bash
# Clone the repository
git clone https://github.com/SaadiMalik1/vireon-lab.git
cd vireon-lab

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package dependencies in editable mode
pip install -e ".[dev]"

# Launch the interactive Streamlit laboratory dashboard
streamlit run vireon_lab/dashboard/app.py
```

Access the dashboard in your web browser at **`http://localhost:8501`**.

---

## 3. Developer & Python SDK Usage

```python
from vireon_lab.engine.circular_buffer import CircularBuffer
from vireon_lab.engine.generators.jansen_rit import JansenRitNeuralMassGenerator
from vireon_lab.engine.artifacts.physiological import EyeBlinkArtifact
from vireon_lab.engine.attacks.mutators import GaussianNoiseAttack

# Initialize O(1) ring buffer (8 channels, 5-minute capacity @ 100 Hz)
ring_buf = CircularBuffer(num_channels=8, capacity=30000)

# Generate biological cortical signals
generator = JansenRitNeuralMassGenerator(num_channels=8)
raw_signals = generator.generate(num_samples=1000, t_start=0.0, sampling_rate=100.0)

# Inject physiological eye-blink artifact
blink_injector = EyeBlinkArtifact()
artifact_signals = blink_injector.inject(raw_signals, t_axis=np.linspace(0, 10, 1000))

# Mutate with Gaussian noise threat vector
mutator = GaussianNoiseAttack()
mutated_signals = mutator.mutate(artifact_signals, t_axis=np.linspace(0, 10, 1000), intensity=1.5)

# Write to ring buffer
ring_buf.write(mutated_signals)
```

---

## 4. Verification & Testing

```bash
# Run unit, integration, and benchmark test suites (70 tests)
pytest

# Code quality & static analysis checks
ruff check vireon_lab tests
mypy vireon_lab
```

---

## 5. Architecture & Documentation

- **[System Architecture Reference](knowledge/architecture.md)**: Specifications for Config, Telemetry RBAC, Middleware, Audit Logging, and Async Workers.
- **[Package Reference](vireon_lab/README.md)**: Developer quickstart and API usage guide for the `vireon_lab` Python package.
- **Underlying Core**: `vireon-lab` depends on `vireon` as its underlying simulation core. Core orchestrator logic, deterministic clocks, and capability engines reside in the **[Vireon](https://github.com/SaadiMalik1/Vireon)** runtime repository.
