# VIREON Installation Guide

**Audience**: Developers, Researchers

VIREON supports Linux, macOS, and Windows Subsystem for Linux (WSL2). Native Windows is not officially supported due to specific Python dependencies (like LSL bindings) that may require manual compilation on Windows.

## 1. System Prerequisites

Before installing the Python package, ensure you have the required system dependencies.

### Rust Toolchain (Required for NeuroDSL DSL)
VIREON uses an embedded Rust compiler to securely execute clinical scripts. You must have Cargo installed with the **nightly** toolchain.
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup default nightly
```

### System Libraries (Debian/Ubuntu)
For the LSL bindings and PDF report generation (WeasyPrint), install the following:
```bash
sudo apt-get update
sudo apt-get install build-essential libpango-1.0-0 libpangoft2-1.0-0
```

## 2. Python Environment Setup

VIREON requires **Python 3.10** or higher. We highly recommend using a virtual environment.

```bash
git clone https://github.com/SaadiMalik1/Vireon.git
cd Vireon

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows WSL use: .venv\Scripts\activate
```

## 3. Install Dependencies

Install the core Python requirements and optional extensions (including Web UI, datasets, and dev tools):
```bash
pip install --upgrade pip
pip install -e ".[all]"
```

*(Optional) PyTorch*: If you intend to use the experimental Deep Autoencoder for the NeuroIDS, you must manually install PyTorch. See the [official PyTorch site](https://pytorch.org/get-started/locally/) for instructions specific to your hardware (CUDA/ROCm/CPU).

## 4. Verification

To verify the installation was successful, run a basic 5-second simulation:
```bash
vireon run --duration 5.0
```

If successful, you will see the Coordinator spin up the Digital Twin, run the tick loop, and gracefully shut down without errors, leaving a PDF report in the root directory.

## 5. Docker Installation (Alternative)

If you prefer to run VIREON without installing host dependencies, a Dockerfile is provided:
```bash
git clone https://github.com/SaadiMalik1/Vireon.git
cd Vireon
docker build -t vireon-lab .
docker run -p 7777:7777 vireon-lab ui --host 0.0.0.0
```

### Dependencies

- Python 3.9+
- Poetry (for package management)
- `liblsl` (for lab streaming layer support)
- Rust Nightly (1.85+) (mandatory for `neuro_dsl` compilation)

> **Note:** macOS users can install LSL via `brew install labstreaminglayer/tap/lsl`. Linux users may need to build from source or install the appropriate binary package. For Rust, use `rustup toolchain install nightly`.

## Troubleshooting
- **Maturin / Rust Build Errors**: If `pip install -e .` fails while building `vireon_neuro_dsl`, ensure Rust is fully updated (`rustup update`) and that you have `maturin` installed (`pip install maturin`).
- **LSL Bindings on Windows**: Native Windows may struggle with `pylsl` binary dependencies. We recommend using WSL2 (Ubuntu) for Windows users.
- **Streamlit Port In Use**: If `vireon ui` fails, another process is using port 7777. Change the port using `vireon ui --port 8888`.
If you encounter other issues, please consult the [FAQ](docs/faq.md) or open a discussion on GitHub.
