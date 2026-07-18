# Migration Guide: Upgrading to VIREON 2.0 (IProvider Architecture)

The Phase 9 architecture refactoring transitions VIREON from a monolithic `Coordinator` and `DigitalTwin` God class structure to a fully decoupled, event-driven runtime using the `IProvider` interface.

This guide outlines the steps required to migrate legacy plugins (which previously relied on direct `DigitalTwin` mutation) to the new `IProvider` architecture.

## Overview of Changes

1. **DigitalTwin Removal:** Plugins must no longer accept or rely on the `DigitalTwin` object for state manipulation.
2. **StateStore & EventBus:** State sharing is now facilitated via the decentralized `StateStore`. Communication is handled entirely through the `EventBus`.
3. **IProvider Interface:** All extensions (firmware, analytics, security, attacks) must now implement the `IProvider` interface.
4. **Capability Manifest:** Every plugin must define a `CapabilityManifest` specifying its required access rights to the runtime.

## Migration Steps

### 1. Implement `IProvider`

Your plugin class must inherit from `vireon.sdk.interfaces.IProvider`.

```python
# Legacy Implementation
class LegacyDetector:
    def __init__(self, twin):
        self.twin = twin
        
    def tick(self):
        # Directly read/write the twin
        current_state = self.twin.hazard_state
        self.twin.update_therapy(False)

# New Implementation
from vireon.sdk.interfaces import IProvider
from vireon.sdk.manifest import CapabilityManifest, Capability

class ModernDetector(IProvider):
    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            name="modern_detector",
            version="1.0.0",
            capabilities=[
                Capability.READ_STATE,
                Capability.PUBLISH_EVENTS
            ]
        )

    def initialize(self, context):
        self.context = context
        # Subscribe to relevant events
        self.context.event_bus.subscribe("experiment.tick", self._on_tick)
```

### 2. Replace Direct State Manipulation

Instead of reading from `self.twin`, use the injected `StateStoreProxy`:

```python
# Old:
# state = self.twin.hazard_state

# New:
state = self.context.state_store.get("hazard_state")
```

Instead of modifying the twin directly to trigger actions, publish events to the `EventBus`:

```python
# Old:
# self.twin.update_therapy(False)

# New:
from vireon.core.event_bus import Event
self.context.event_bus.publish(Event(
    topic="therapy.disable",
    data={"reason": "anomaly_detected"},
    source=self.manifest.name
))
```

### 3. Capability Declaration

Ensure your manifest explicitly declares the capabilities you use. If you attempt to write to the `StateStore` without the `WRITE_STATE` capability, the `CapabilityEngine` will deny the transaction and raise a `PermissionError`.

## Conclusion
Migrating to `IProvider` ensures your plugin is isolated, secure, and compatible with both in-process and subprocess execution contexts.
