# API & Interfaces Reference

**Audience**: Developers, Data Scientists

*Note: The interfaces described below represent the logical components of the system. In the current prototype implementation, these modules are tightly coupled and run synchronously on the main Python thread.*

## Core Modules (`vireon.core`)

### `Coordinator`
The central orchestrator of the simulation.
- `setup()`: Initializes the Digital Twin, Firmware Emulator, LSL Streamers, and ZTA Engine.
- `run_simulation()`: Enters the blocking tick-based physics loop.

### `SecurityEngine` / `NeuroIPS`
The heuristic threat intelligence and zero-trust evaluation core.
- `evaluate_request(action, context)`: Evaluates trust context against physical anomalies.

### `DigitalTwin`
Models the physiological and physical state of the patient/device.
- `tick(time_delta, active_draw)`: Advances state of battery and temperature.
- `set_clinical_alert(status, reason)`: Flags anomalies.

### `EventBus`
Global pub-sub broker for synchronous event dispatch across plugins and engines.
- `subscribe(event_type, callback)`
- `publish(event_type, payload)`

## Engines & Emulators

### `NeuroIPS`
The Intrusion Prevention System. Intercepts `EventBus` messages and blocks malicious instructions before they hit the DigitalTwin.

### `BLE Emulator`
Simulates the Bluetooth Low Energy interface of clinical programmers.
- `inject_packet(payload)`: Simulates over-the-air injection.
- `read_characteristic(uuid)`: Fetches simulated device state.

## Abstract Interfaces (`vireon.core.plugin`)

### `ISignalModifier`
Abstract base interface for all attack and mitigation plugins (e.g., NoiseInjectionAttack, SignalDriftAttack).

### `BaseDataset`
Interface for dataset readers. Returns standard NumPy arrays for `Coordinator` playback.

### `PluginRegistry`
Singleton manager for dynamically loaded capabilities.
- `register(plugin_type, class_ref)`
- `list_category(category)`

## CLI (`__main__.py`)
The `main.py` entry point exposes the `vireon` CLI via Click.
- `run`: Headless simulation.
- `ui`: Streamlit dashboard.
- `fuzz`: Protocol fuzzing.
- `sbom`: FDA 524B compliance exports.
- `compile`: Compiles NeuroDSL scripts.
- `info`: Lists loaded plugins.

## Configuration (`vireon.core.config`)
- `ExperimentConfig`: Strongly-typed Pydantic model for loading and validating `default.toml` constraints (replaces loose dictionaries).
