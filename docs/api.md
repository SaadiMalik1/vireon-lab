# API & Interfaces Reference

**Audience**: Developers, Data Scientists

## Python API (Core Modules)

VIREON's core functionality is encapsulated within the `vireon.core` namespace. This reference provides an overview of the primary classes you will interact with when writing scripts or plugins.

### `vireon.core.coordinator.Coordinator`
The central orchestrator of the simulation.
- `__init__(config: Configuration, output_dir: str)`
- `setup()`: Initializes the Digital Twin, Firmware Emulator, LSL Streamers, and ZTA Engine based on the provided configuration.
- `run_simulation()`: Enters the blocking tick-based physics loop.
- `simulate_firmware_update(payload: bytes) -> bool`: Simulates an OTA update. Internally calls the ZTA engine to evaluate trust before proceeding.

### `vireon.core.zta.ZTAPolicyEngine`
The Zero-Trust authorization engine.
- `__init__(thresholds: dict)`: Initializes action-specific trust thresholds.
- `evaluate_request(action: str, context: TrustContext) -> AuthorizationDecision`: Evaluates if the current `TrustContext` meets the threshold for the requested action.

### `vireon.core.twin.DigitalTwin`
Models the physiological and physical state of the patient/device.
- `tick(time_delta: float, active_draw: float)`: Advances the state of the battery and tissue temperature based on power draw.
- `set_clinical_alert(status: bool, reason: str)`: Flags an anomaly for the reporting engine.

---

## Command Line Interface (CLI)

The `main.py` entry point exposes the VIREON CLI via `click`.

### `run`
Executes a headless simulation.
```bash
python3 -m vireon run [OPTIONS]
```
- `--duration FLOAT`: Duration of the simulation in seconds (default: 10.0).
- `--attack TEXT`: Pre-configured attack to inject (options: `mtu`, `noise`, `rollback`, `none`).

### `ui`
Launches the Streamlit diagnostic dashboard.
```bash
python3 -m vireon ui [OPTIONS]
```
- `--port INTEGER`: Port to bind the dashboard to (default: 7777).

---

## Telemetry Interfaces

VIREON emits two data streams synchronously during a simulation run.

### Lab Streaming Layer (LSL)
- **Stream Name**: `NeuroShield_EEG`
- **Type**: `EEG`
- **Channels**: 8
- **Sample Rate**: 250 Hz
- **Format**: `float32`

### WebSockets (Diagnostic State)
- **Port**: 8765 (default)
- **Format**: JSON
- **Payload Structure**:
  ```json
  {
    "time": 1.25,
    "battery_capacity": 499.5,
    "temperature": 37.1,
    "cpu_usage": 15.0,
    "firmware_crashed": false,
    "zta_score": 0.95,
    "alerts": []
  }
  ```
