# Frequently Asked Questions (FAQ)

**Audience**: End Users, Developers

## Installation & Setup

### 1. The simulation crashes with a `maturin` or `Rust` error.
VIREON uses `maturin` to compile the `neuro_dsl` Rust extension on the fly during `pip install` (or during testing). 
- Ensure you have the Rust toolchain installed (`cargo --version`, requires 1.85+).
- Ensure you are building from the root of the repository where the `pyproject.toml` correctly points to the `neuro_dsl/` directory.

### 2. I get a "libpango" error when the simulation finishes.
VIREON uses `weasyprint` to generate the end-of-simulation PDF reports. This requires system-level Pango and Cairo libraries. 
- On Ubuntu/Debian: `sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0`
- On macOS: `brew install pango`

### 3. Does VIREON run on Windows?
Native Windows is not officially supported due to specific Python dependencies (like LSL bindings) that may require manual compilation on Windows. We strongly recommend using **Windows Subsystem for Linux (WSL2)** running Ubuntu.

### 4. Can I use Docker?
Yes! A Dockerfile is provided. You can build and run it using:
```bash
docker build -t vireon-lab .
docker run -p 7777:7777 vireon-lab ui --host 0.0.0.0
```

### 5. What are the system requirements?
- **OS**: Linux, macOS, or Windows WSL2
- **Language**: Python 3.10+ and Rust 1.85+
- **Memory**: Minimum 4GB RAM recommended for running simulations and the Web UI simultaneously.

## Running Simulations

### 6. Why is the Streamlit dashboard empty?
The Streamlit dashboard (`vireon ui`) connects to the simulation via WebSockets. It will remain empty until you start an active simulation in a separate terminal window (`vireon run`).

### 7. How do I capture the EEG data for analysis in EEGLAB or Python?
VIREON broadcasts EEG data using the Lab Streaming Layer (LSL). You can use any standard LSL viewer or write a simple Python script using `pylsl` to resolve the stream named `VIREON_EEG` and pull chunks in real-time.

### 8. Can I use real EEG data instead of synthetic noise?
Yes. You can load standard clinical data formats (like `.edf`) by passing them to the CLI:
`vireon run --dataset=patient_data.edf`

### 9. Can I connect a real BCI or DBS device?
Currently, Hardware-in-the-Loop (HIL) testing is highly experimental and limited to OpenBCI boards. See the tutorials for setting up HIL.

### 10. The simulation is running much slower than real-time.
Check your `SecurityConfig`. If you have the PyTorch Deep Autoencoder enabled, it adds latency per tick. If you do not have a dedicated GPU, this will cause the simulation clock to lag behind wall-clock time. Disable it in the configuration to fall back to the ultra-fast Linear Autoencoder.

### 11. Are the benchmark results exactly reproducible?
Benchmarks (like sub-millisecond latency claims) lack statistical rigor due to Python's Global Interpreter Lock (GIL) and standard OS scheduler noise. They serve as estimates rather than guaranteed hard real-time metrics.

## Threat Modeling & Security

### 12. Can VIREON simulate physical RF jamming?
No. As outlined in the [Threat Model bounds](threat-model/assumptions.md), we do not simulate the PHY layer. VIREON only models logical attacks like MTU abuse or malformed GATT packets.

### 13. Is the cryptography in VIREON secure?
**NO**. VIREON uses **simulated cryptography** (e.g., XOR patterns) designed solely for threat modeling and timing analysis. Do NOT use VIREON for mathematical security or production environments.

### 14. How do I add my own attack?
You can create a new Python class inheriting from `BaseAttack` and place it in the `vireon.attacks` namespace (or inject it dynamically via the Plugin Registry). See the [Plugin Development Guide](plugin-development.md) for details.

## Contributing

### 15. How can I contribute to VIREON?
We welcome contributions from researchers and engineers! Please read our `CONTRIBUTING.md` for guidelines on submitting Pull Requests.
