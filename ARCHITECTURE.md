# VIREON Architecture Extraction

## 1. Overview and Subsystem Boundaries

The VIREON repository is structured around a central simulation core, extended via a plugin registry, and observed via a web dashboard and external streaming protocols.

### Subsystem Boundaries
- **Core Orchestration (`vireon.core`)**: Contains the primary state machines and orchestration logic (`Coordinator`, `ReplayEngine`, `DigitalTwin`, `EventBus`).
- **Plugin Ecosystem (`vireon.plugins`)**: Contains specific vendor implementations, hardware-in-the-loop (HIL) emulators, and clinical controllers.
- **Security & Compliance (`vireon.core` and `threat_models`)**: Contains the intrusion detection systems, Zero-Trust Architecture (ZTA) engines, and adversarial attack scenarios.
- **User Interface (`vireon.dashboard`)**: A Streamlit-based web application for observing real-time telemetry.

## 2. Identified Modules

- **Coordinator** (`core/coordinator.py`): The main entry point that wires components together.
- **Digital Twin** (`core/twin.py`): The authoritative state machine for physiological, hardware, and clinical states.
- **Replay Engine** (`core/engine.py`): The time-stepping simulation loop that pushes data.
- **Event Bus** (`core/event_bus.py`): The pub/sub mechanism for inter-component messaging.
- **Plugin Registry** (`core/plugin_registry.py`): Discovers and instantiates loosely-coupled modules.
- **Attack Engine** (`core/attack_factory.py`, `core/attack/`): Executes specific adversarial techniques against the twin.
- **Physics Engine** (`core/physics.py`): Calculates thermodynamics, battery sag, and impedance.
- **Clinical Engine** (`core/clinical.py`): Evaluates medical status and triggers interventions.

## 3. Dependency Analysis and Coupling

### God Classes
- **`Coordinator`**: Violates the Single Responsibility Principle. It knows about every possible subsystem (BLE, WebSockets, specific emulators like OpenBCI, ZTA engines, and Threat Intel) and explicitly imports them during `setup()`.
- **`DigitalTwin`**: Violates interface segregation. It acts as a massive data class mixing hardware state (battery, BLE), clinical state (seizures), and security state (red team alerts).

### Circular Dependencies
- Historically, `utils.py` and `event_bus.py` exhibited circular dependencies. While recently remediated, the architecture remains highly prone to tight coupling due to the lack of strict interface contracts between core engines.

### Execution Flow & Runtime Lifecycle
1. **Setup**: `Coordinator` receives an `ExperimentConfig` and instantiates the `DigitalTwin`, `EventBus`, and `PluginRegistry`.
2. **Wiring**: It registers built-in plugins, configures attacks, and explicitly instantiates active components (e.g., `ClosedLoopDBSController`, `ids`).
3. **Looping**: `ReplayEngine.start()` runs the main thread. In each tick, it advances the `sim_clock`, processes incoming EEG data, runs the physics simulation, and triggers `simulation_callback`.
4. **Telemetry**: Callbacks serialize the state and push telemetry over WebSockets to the Dashboard.
5. **Teardown**: `Coordinator.teardown()` halts engines and compiles reports.

## 4. Extension Points and Plugin Mechanisms

- **`PluginRegistry`**: Exposes a `create(category, name, **kwargs)` method. This allows dependency injection, but relies heavily on string mapping.
- **`EventBus`**: Allows any component to `subscribe()` to specific topics, decoupling event producers from consumers.
- **NeuroDSL (Rust Stack)**: Allows execution of compiled bytecode, but lacks sandboxing, meaning scripts execute directly in the host process memory.

## 5. Ownership Boundaries

- The **Framework** owns the `EventBus`, `ReplayEngine`, and scheduling.
- **Plugins** (e.g., DBS Controller, OpenBCI emulator) own the logic of specific biomedical interventions or hardware translations.
- However, ownership boundaries are currently violated because the `Coordinator` (Framework) hardcodes the instantiation logic of specific plugins (e.g., `from vireon.plugins.clinical.dbs_emulator import ClosedLoopDBSController`).

## 6. Architectural Conclusion

### Strengths
- **Modular Data Routing**: The `EventBus` provides a robust, decoupled way for disconnected systems (like dashboards and loggers) to observe state.
- **Declarative Configuration**: Moving to `ExperimentConfig` with Pydantic ensures types are verified before the simulation begins.
- **Ecosystem Readiness**: The existence of `PluginRegistry` proves the framework is preparing for vendor extensibility.

### Weaknesses
- **Tight Coupling in Orchestration**: The `Coordinator` knows too much about concrete implementations, making it difficult to swap out providers without changing core framework code.
- **Lack of Sandboxing**: Plugins execute in the same memory space as the framework. A malicious or buggy plugin can hang the simulation or bypass security controls.
- **State Bloat**: `DigitalTwin` contains hardcoded properties for specific use cases (e.g., `nsp_mode`), violating the vendor-neutral principle.

### Technical Debt
- Direct import of concrete implementations inside `coordinator.py`.
- Synchronous execution of attacks and plugins within the primary `ReplayEngine` loop, which introduces severe latency if a plugin blocks.
- Telemetry generation directly tied to the simulation tick, preventing asynchronous state observation.

### Architectural Risks
1. **Extensibility Risk**: Vendors cannot provide independent plugins if the `Coordinator` must be updated to know about them.
2. **Security Risk**: The absence of a capability manifest means any loaded plugin has full, unfettered access to mutate the `DigitalTwin` state.
3. **Performance Risk**: The unified lock (`threading.RLock`) in `DigitalTwin` ensures safety but will cripple performance as the number of parallel plugins increases.
