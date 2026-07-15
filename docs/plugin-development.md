# Plugin Development Guide

**Audience**: Developers, Security Researchers

VIREON utilizes an event-driven architecture, making it highly extensible. You can inject new threat models, custom telemetry sinks, or custom hardware emulators without modifying the core `vireon` namespace.

## 1. The Event Bus
All cross-component communication happens via the `EventBus`. The Coordinator, Digital Twin, and all Plugins share this bus.

**Common Events**:
- `SIMULATION_START`: Fired when the tick loop begins.
- `TICK_COMPLETE`: Fired at the end of every simulation tick. Payload includes the current physical state.
- `ATTACK_INJECTED`: Fired when an attack payload is delivered to the firmware.
- `FIRMWARE_CRASH`: Fired if the emulator halts unexpectedly.

## 2. Adding Custom Components

### Custom Attack Plugins
To write a custom attack, inherit from `BaseAttack`.
```python
from vireon.core.attack import BaseAttack

class CustomDenialOfServiceAttack(BaseAttack):
    def __init__(self, target_twin, flood_rate: int = 100):
        super().__init__(target_twin)
        self.flood_rate = flood_rate

    def apply(self, client, link):
        for _ in range(self.flood_rate):
            link.inject_malformed_packet(b"\xFF\x00")
```

### New Device Types
To emulate a new BCI or DBS device, extend `vireon.core.device.BaseDevice` and implement the `tick()` behavior.

### Dataset Readers
To parse custom data formats (e.g., specific clinical `.mat` structures), inherit from `vireon.core.dataset.BaseDataset`.

### Report Formats
Custom reporters (e.g., XML output) can be added by implementing the `vireon.core.reporting.BaseReporter` interface.

## 3. Configuration & Registration
Plugins can read from their own sections in `default.toml` by utilizing the `PluginConfig` class.

Plugins are registered using the `PluginRegistry` in `__main__.py` or via standard Python entry points in `pyproject.toml`:
```toml
[project.entry-points."vireon.plugins"]
my_attack = "my_package:get_plugin_info"
```

## 4. Testing & Validation
All custom plugins must be unit-tested. Use the provided `MockCoordinator` in `vireon.tests.mocks` to simulate event bus dispatch without running a full clinical simulation.

## 5. Rust Workflow (NeuroDSL)
If your plugin extends the NeuroDSL compiler (e.g., adding a new firmware instruction):
1. Navigate to `neuro_dsl/forge` or `neuro_dsl/scribe`.
2. Add your implementation in Rust.
3. Run `cargo test` to verify.
4. Run `maturin develop` from the Python root to rebuild the bindings.

## 6. Release Process
To distribute your plugin:
- Package it as a standard Python module on PyPI.
- Ensure the `vireon.plugins` entry point is defined.
- Users can then run `pip install your-vireon-plugin` and it will automatically appear in `vireon info`.
