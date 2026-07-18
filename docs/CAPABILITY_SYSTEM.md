# Phase 4: Capability System Design

## 1. Goal
The runtime should discover providers automatically, and strictly enforce security and resource boundaries. No plugin should have implicit trust.

## 2. Capability Manifest
Each plugin must declare its capabilities in a `Manifest`.

```yaml
# example_manifest.yaml
provider_name: "vendor_x_firmware"
version: "1.2.0"
category: "firmware"
author: "Vendor X"

capabilities:
  # Topics this provider is allowed to publish to
  publishes:
    - "device.stimulate"
    - "device.telemetry"
  
  # Topics this provider is allowed to subscribe to
  subscribes:
    - "system.tick"
    - "clinical.eeg"

  # State store keys this provider can mutate
  mutates_state:
    - "battery_level"
    - "cpu_cycles"

  # State store keys this provider can read
  reads_state:
    - "temperature"
    - "impedance"

  # System-level risky capabilities
  system:
    - "network_access"       # Requires user approval
    - "spawn_subprocess"     # Requires user approval
```

## 3. Capability Resolution & Feature Negotiation
During the `RESOLUTION` phase of the Orchestrator lifecycle:
1. The `CapabilityEngine` reads the manifest.
2. It compares the requested capabilities against the `ExperimentConfig`'s policy.
3. If a plugin requests `network_access` but the experiment policy runs in `strict_offline` mode, the resolution fails, and the Orchestrator aborts.
4. If successful, the Orchestrator provisions an isolated `EventBus` proxy and `StateStore` proxy for that specific plugin.

## 4. Dependency Injection
Plugins do not instantiate their own dependencies. The Orchestrator injects proxies:
```python
class IFirmwareProvider(IProvider):
    def initialize(self, context: OrchestratorContext):
        self.bus = context.event_bus  # This is a proxy!
        self.state = context.state_store # This is a proxy!
```
The proxies enforce the manifest at runtime. If `vendor_x_firmware` calls `self.bus.publish("unauthorized_topic", data)`, the proxy throws a `CapabilityViolationError`.

## 5. Version Compatibility
Providers must specify semantic versioning dependencies:
```yaml
dependencies:
  - provider: "core.physics"
    version: ">=2.0.0"
```
The `PluginRegistry` resolves a dependency graph before initializing. If version conflicts occur, it panics.

## 6. Plugin Discovery
Plugins are discovered via:
1. `vireon.plugins` entry points (Python standard).
2. Explicit paths in `ExperimentConfig`.
3. Auto-scanning the `~/.vireon/plugins/` directory for zipped provider bundles.

## 7. Runtime Validation
The `CapabilityEngine` remains active at runtime. Every IPC message, RPC call, or state mutation is intercepted by the capability proxy. This prevents zero-day exploits in plugins from escalating into full framework compromise.
