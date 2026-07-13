# Frequently Asked Questions (FAQ)

**Audience**: End Users, Developers

## Installation & Setup

### 1. The simulation crashes with a `maturin` or `Rust` error.
VIREON uses `maturin` to compile the `runemate` Rust extension on the fly during `pip install` (or during testing). 
- Ensure you have the Rust toolchain installed (`cargo --version`).
- Ensure you are building from the root of the repository where the `pyproject.toml` correctly points to the `runemate/` directory.

### 2. I get a "libpango" error when the simulation finishes.
VIREON uses `weasyprint` to generate the end-of-simulation PDF reports. This requires system-level Pango and Cairo libraries. 
- On Ubuntu/Debian: `sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0`
- On macOS: `brew install pango`

## Running Simulations

### 3. Why is the Streamlit dashboard empty?
The Streamlit dashboard (`python3 -m vireon ui`) connects to the simulation via WebSockets. It will remain empty until you start an active simulation in a separate terminal window (`python3 -m vireon run`).

### 4. How do I capture the EEG data for analysis in EEGLAB or Python?
VIREON broadcasts EEG data using the Lab Streaming Layer (LSL). You can use any standard LSL viewer or write a simple Python script using `pylsl` to resolve the stream named `NeuroShield_EEG` and pull chunks in real-time.

### 5. The simulation is running much slower than real-time.
Check your `SecurityConfig`. If you have the PyTorch Deep Autoencoder enabled, it adds ~50ms of latency per tick. If you do not have a dedicated GPU, this will cause the simulation clock to lag behind wall-clock time. Disable it in the configuration to fall back to the ultra-fast Linear Autoencoder.

## Threat Modeling

### 6. Can VIREON simulate physical RF jamming?
No. As outlined in the [Threat Model bounds](threat-model/assumptions.md), we do not simulate the PHY layer. VIREON only models logical attacks like MTU abuse or malformed GATT packets.

### 7. How do I add my own attack?
You can create a new Python class inheriting from `BaseAttack` and place it in the `vireon.attacks` namespace (or inject it dynamically via the Plugin Registry). See the [Plugin Development Guide](plugin-development.md) for details.
