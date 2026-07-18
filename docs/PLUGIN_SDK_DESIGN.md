# Phase 3: Plugin SDK Design

## 1. Goal
Design a unified Plugin SDK to replace all ad-hoc extension mechanisms. Everything in VIREON (firmware, protocols, threat models, physics, clinical models) must become a Provider. 

## 2. Universal Provider Architecture
Instead of specific classes inheriting from bespoke base classes in different modules, all plugins must implement a universal `IProvider` interface.

### The `IProvider` Interface
Every provider must implement the following base interface:
```python
class IProvider:
    @property
    def manifest(self) -> CapabilityManifest:
        """Returns the capabilities required by this provider."""
        pass
        
    def initialize(self, context: OrchestratorContext) -> None:
        """Called by the Orchestrator after capabilities are resolved."""
        pass
        
    def on_tick(self, sim_clock: float, dt: float) -> None:
        """Called every simulation tick if the provider subscribes to time."""
        pass
        
    def shutdown(self) -> None:
        """Called during graceful shutdown."""
        pass
```

## 3. Provider Categories

### 3.1 Firmware Provider
- **Responsibilities**: Execute payload instructions, simulate CPU cycles, handle memory read/write requests, manage OTA update payloads.
- **Lifecycle**: Boot -> Execute -> Fault/Shutdown.
- **Interfaces**: `IFirmwareProvider` (extends `IProvider`). Adds `write_memory(address, data)`, `read_memory(address)`.
- **Versioning**: Tied to ARM architecture versions (e.g., Cortex-M4v1).
- **Dependency Rules**: Cannot depend on Clinical or Physics providers directly.

### 3.2 Protocol Provider
- **Responsibilities**: Translate raw byte payloads into logical telemetry frames (e.g., BLE, proprietary RF).
- **Lifecycle**: Bound to network socket or simulated radio interface.
- **Interfaces**: `IProtocolProvider`. Adds `encode(frame) -> bytes`, `decode(bytes) -> frame`.
- **Versioning**: SemVer based on protocol specification.

### 3.3 Threat Model Provider
- **Responsibilities**: Define declarative attack trees, STRIDE boundaries, and required exploit capabilities.
- **Lifecycle**: Read-only during Setup.
- **Interfaces**: `IThreatModelProvider`. Returns structured STIX/TARA graphs.

### 3.4 Physics Provider
- **Responsibilities**: Simulate thermodynamics, battery chemistry, and electrical impedance.
- **Lifecycle**: Stateful, updated every `dt` tick.
- **Interfaces**: `IPhysicsProvider`. Subscribes to `device.stimulate`, publishes `physics.state_update`.

### 3.5 Clinical Provider
- **Responsibilities**: Emulate neurophysiological responses to stimulation (e.g., seizure suppression, biomarker shifts).
- **Lifecycle**: Stateful, updated every `dt` tick.
- **Interfaces**: `IClinicalProvider`. Subscribes to `device.stimulate` and `physics.state_update`, publishes `clinical.eeg`.

### 3.6 Validation & Reporting Providers
- **Responsibilities**: Assert success criteria, track ISO compliance, and generate HTML/PDF output.
- **Lifecycle**: Subscribes to all telemetry passively. Executes heavily during `Teardown`.

## 4. Capability Manifest
Each provider explicitly defines its boundaries:
```python
class CapabilityManifest:
    name: str
    version: str
    category: str
    publishes_events: List[str]
    subscribes_events: List[str]
    mutates_state: List[str]
    reads_state: List[str]
    requires_host_access: bool
```
The SDK will provide decorators to statically generate these manifests.

## 5. Dependency Rules
- Providers NEVER import each other's concrete classes.
- If a Clinical provider needs Firmware state, it must read from the `StateStore` (if granted Capability) or listen to an `EventBus` topic.
- The SDK package (`vireon.sdk`) must be zero-dependency (no Pandas, no PyTorch) so vendors can import it cleanly.
