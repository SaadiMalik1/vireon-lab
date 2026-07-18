# Plugin Development Guide

**Audience**: Firmware Developers, Ecosystem Vendors, Security Researchers

VIREON utilizes a strict, event-driven ecosystem architecture. Third-party vendors and external contributors must implement against the frozen `vireon.sdk` boundary. The Core framework guarantees that your code will be sandboxed and orchestrated according to the formal plugin lifecycle.

## 1. The `IVireonPlugin` Interface

All plugins must implement the `vireon.sdk.plugin.IVireonPlugin` abstract base class. This is the sole entry point recognized by the VIREON runtime.

```python
from vireon.sdk.plugin import IVireonPlugin
from vireon.sdk.events import Event

class VendorFirmwarePlugin(IVireonPlugin):
    @property
    def manifest(self) -> dict:
        return {
            "name": "Vendor Firmware Emulation",
            "version": "1.0.0",
            "capabilities_requested": ["NETWORK_ACCESS", "STATE_MUTATION"]
        }

    def initialize(self, context):
        self.bus = context.event_bus
        self.store = context.state_store
        # Do not start threads here. See PLUGIN_LIFECYCLE.md.

    def start(self):
        # Called when the Run phase is reached.
        pass

    def shutdown(self):
        # Graceful cleanup.
        pass
```

## 2. The 10-Phase Lifecycle

Your plugin will be managed by the Core Orchestrator through a rigid 10-phase state machine:

1. **Discover**: The Orchestrator locates your package.
2. **Validate**: The `manifest` property is parsed and validated against schema rules.
3. **Load**: Your `IVireonPlugin` class is instantiated.
4. **Initialize**: `initialize(context)` is called. You receive your isolated handles to `IEventBus` and `IStateStore`.
5. **Capability Negotiation**: The Orchestrator verifies your requested capabilities.
6. **Run**: The simulation loop begins. `start()` is invoked.
7. **Suspend**: Invoked during pauses. You must halt active processing.
8. **Resume**: Wakes up from suspension.
9. **Unload**: Preparing for teardown.
10. **Shutdown**: `shutdown()` is called to release sockets/files.

For an exhaustive breakdown of these phases, see [Plugin Lifecycle Management](PLUGIN_LIFECYCLE.md).

## 3. The Event Bus
Cross-component communication happens strictly via the `IEventBus` provided in your initialization context.

**Subscribing to Events**:
```python
def on_tick(self, event: Event):
    physical_state = event.payload
    # Mutate emulator logic

self.bus.subscribe("TICK_COMPLETE", self.on_tick)
```

**Publishing Events**:
```python
alert = Event(topic="FIRMWARE_CRASH", payload={"reason": "OOM"})
self.bus.publish(alert)
```

## 4. Configuration & Registration

Your plugin should export its `IVireonPlugin` subclass via the standard Python entry point in your `pyproject.toml` (even if developed in an external repository):

```toml
[project.entry-points."vireon.plugins"]
my_vendor_firmware = "my_external_package:VendorFirmwarePlugin"
```

The VIREON core will automatically discover and load it during the **Discover** phase.

## 5. Testing & Validation

All custom plugins must be validated against the `VIREON Framework` before release. We highly recommend writing integration tests using a mocked `IEventBus` and `IStateStore` from `vireon.sdk.testing`.

For deep integration testing strategies (including how to run tests against the compiled Rust NeuroDSL scripts), refer to the [Testing Architecture](TESTING_ARCHITECTURE.md) document.

## 6. Rust Workflow (NeuroDSL)
If your plugin extends the NeuroDSL compiler (e.g., adding a new firmware instruction to `Scribe`):
1. Navigate to your custom `neuro_dsl` extensions.
2. Build the implementation in Rust.
3. Use the unified bindings pattern defined in `vireon.sdk` to inject your custom OpCodes into the engine.
