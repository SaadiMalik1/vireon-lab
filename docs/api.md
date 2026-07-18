# API & Interfaces Reference

**Audience**: Framework Maintainers, External Vendors, Data Scientists

The VIREON ecosystem strictly enforces Dependency Inversion. External vendors interact with the core simulation solely through the frozen `vireon.sdk` boundaries. Internal orchestration logic resides in `vireon.core`.

## The Public SDK (`vireon.sdk`)

The `vireon.sdk` module provides the abstract contracts necessary for building compatible third-party plugins. This boundary is statically guaranteed and enforces backward compatibility.

### `IVireonPlugin`
The single entry point base class for all third-party firmware, emulators, and analytical decoders.
- `manifest`: Property returning a dictionary with the plugin's metadata and requested capabilities.
- `initialize(context)`: Called during phase 4 of the lifecycle. Provided an `OrchestratorContext`.
- `start()`: Called when the simulation transitions to the `Run` state.
- `shutdown()`: Invoked upon termination for resource cleanup.

### `IEventBus`
The globally accessible interface for asynchronous message dispatch.
- `subscribe(topic: str, callback: Callable)`
- `publish(event: Event)`

### `IStateStore`
The deterministic, lock-free interface replacing the legacy `DigitalTwin`. It guarantees authoritative read/write access to physical and clinical variables.
- `get(key: str)`
- `set(key: str, value: Any)`
- `increment(key: str, value: float)`

### `Event`
The standard data carrier for pub-sub messaging.
- `topic`: String indicating the event type.
- `payload`: Dictionary containing serializable event data.

---

## Core Orchestration (`vireon.core`)

The `vireon.core` namespace handles the internal lifecycle and physics orchestration. **Third-party code must not import from this namespace.**

### `Orchestrator`
The central state machine that manages the 10-phase plugin lifecycle (Discover -> ... -> Shutdown).
- `load_plugins()`: Scans the registry and instantiates objects.
- `start()`: Enters the physics time-stepping loop.

### `SecurityEngine` / `NeuroIPS`
The heuristic threat intelligence and zero-trust evaluation core.
- `evaluate_request(action, context)`: Assesses physical anomalies and blocks unverified state transitions before they reach the `StateStore`.

### `PhysicsEngine`
Calculates thermodynamics, battery sag, and electrical impedance across the `StateStore`.

---

## The Educational Toolkit (`vireon_lab`)

The `vireon_lab` directory contains implementations built *on top of* the `vireon.sdk`.

### `Web Dashboard`
An interactive Streamlit application that consumes the `IEventBus` over WebSockets to display telemetry.

### `Educational Providers`
Implementations of `IVireonPlugin` that emulate real-world BCIs for educational CTFs (e.g., the OpenBCI emulator, QEMU HIL bridge).

---

## CLI (`__main__.py`)
The `main.py` entry point exposes the `vireon` CLI via Click.
- `run`: Headless simulation.
- `ui`: Streamlit dashboard.
- `fuzz`: Protocol fuzzing.
- `sbom`: FDA 524B compliance exports.
- `compile`: Compiles NeuroDSL scripts.
- `info`: Lists loaded plugins and their negotiated capabilities.

## Configuration
- `ExperimentConfig`: Strongly-typed Pydantic model for loading and validating `default.toml` constraints.
