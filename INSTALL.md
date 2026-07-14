# NeuroShield Installation Guide

**Audience**: Developers, Researchers

NeuroShield supports Linux, macOS, and Windows Subsystem for Linux (WSL2). Native Windows is not officially supported due to specific Python dependencies (like LSL bindings) that may require manual compilation on Windows.

## 1. System Prerequisites

Before installing the Python package, ensure you have the required system dependencies.

### Rust Toolchain (Required for NeuroDSL DSL)
NeuroShield uses an embedded Rust compiler to securely execute clinical scripts. You must have Cargo installed.
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### System Libraries (Debian/Ubuntu)
For the LSL bindings and PDF report generation (WeasyPrint), install the following:
```bash
sudo apt-get update
sudo apt-get install build-essential libpango-1.0-0 libpangoft2-1.0-0
```

## 2. Python Environment Setup

NeuroShield requires **Python 3.10** or higher. We highly recommend using a virtual environment.

```bash
git clone https://github.com/SaadiMalik1/neurosheild.git
cd neurosheild

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows WSL use: .venv\Scripts\activate
```

## 3. Install Dependencies

Install the core Python requirements:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

*(Optional) PyTorch*: If you intend to use the experimental Deep Autoencoder for the NeuroIDS, you must manually install PyTorch. See the [official PyTorch site](https://pytorch.org/get-started/locally/) for instructions specific to your hardware (CUDA/ROCm/CPU).

## 4. Verification

To verify the installation was successful, run a basic 5-second simulation:
```bash
python3 -m neuroshield run --duration 5.0
```

If successful, you will see the Coordinator spin up the Digital Twin, run the tick loop, and gracefully shut down without errors, leaving a PDF report in the root directory.

## Troubleshooting
If you encounter issues during installation, please consult the [FAQ](docs/FAQ.md) or open a discussion on GitHub.
