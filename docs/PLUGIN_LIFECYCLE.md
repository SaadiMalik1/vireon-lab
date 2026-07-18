# Plugin Lifecycle Management

To ensure deterministic behavior, resource safety, and secure capability isolation, all VIREON plugins must adhere to a strict state machine lifecycle managed by the Core Orchestrator. 

## The 10-Phase Lifecycle

### 1. Discover
The Orchestrator scans configured plugin directories or endpoints. It looks for valid package structures containing an implementation of `IVireonPlugin`. At this phase, no third-party code is executed.

### 2. Validate
The Orchestrator statically parses the plugin's `manifest` property or `manifest.json`. It verifies cryptographic signatures (if enabled), checks framework SDK compatibility, and ensures requested capabilities are well-formed.

### 3. Load
The plugin module is dynamically imported into the Python runtime. The `IVireonPlugin` class is instantiated. Constructor logic must be minimal, purely allocating necessary internal state without acquiring external resources or starting threads.

### 4. Initialize
The Orchestrator invokes `plugin.initialize(context)`. The plugin is handed an `OrchestratorContext` containing strictly scoped references to the `IEventBus` and `IStateStore`. The plugin sets up its internal routes and prepares for execution.

### 5. Capability Negotiation
The Orchestrator evaluates the plugin's requested capabilities against the global security policy. If the plugin requests `NetworkAccess` but the runtime is configured in offline mode, negotiation fails, and the plugin is transitioned directly to `Shutdown`.

### 6. Run
The Orchestrator starts the simulation loop. The plugin's `start()` method is called (for active providers), or its `on_tick(sim_clock, dt)` method begins receiving regular invocations. The plugin actively processes data, modifies state, and publishes events.

### 7. Suspend
Triggered by the Orchestrator during debugging, pause requests, or resource contention. The plugin must immediately halt active processing, stop emitting events, and save any volatile state. Network connections may be kept alive but must not transmit payload data.

### 8. Resume
The Orchestrator signals the plugin to wake up from suspension. Time-sensitive logic must account for the delta elapsed during the suspension window.

### 9. Unload
Triggered prior to system termination or during hot-reloading. The plugin must unregister from all event bus topics and flush any pending data.

### 10. Shutdown
The terminal state. The plugin's `shutdown()` method is called. The plugin must release all system resources (sockets, file handles, subprocesses). After this phase, the object is dereferenced for garbage collection.
