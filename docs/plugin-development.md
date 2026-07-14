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

## 2. Writing a Custom Attack Plugin

To write a custom attack, inherit from the `BaseAttack` abstract class.

```python
from vireon.core.attack import BaseAttack

class CustomDenialOfServiceAttack(BaseAttack):
    """
    Simulates a DoS attack by flooding the firmware event queue.
    """
    
    def __init__(self, target_twin, flood_rate: int = 100):
        super().__init__(target_twin)
        self.flood_rate = flood_rate

    def apply(self, client, link):
        # Your attack logic here.
        # Use the provided BLE client or direct link to inject packets.
        for _ in range(self.flood_rate):
            link.inject_malformed_packet(b"\xFF\x00")
            
        print(f"Injected {self.flood_rate} malformed packets.")
```

## 3. Registering the Plugin

Plugins must be registered with the Coordinator before the simulation begins. If you are using the CLI, this currently requires modifying the `setup()` block in `main.py`. In future versions, dynamic loading via entry points will be supported.

```python
# In main.py
coordinator = Coordinator(config, run_dir)
coordinator.setup()

# Inject custom attack
my_attack = CustomDenialOfServiceAttack(coordinator.twin, flood_rate=500)
my_attack.apply(coordinator.ble_client, coordinator.ble_link)
```

## 4. Threat Intelligence Mapping

If your custom attack maps to a known theoretical neurosecurity threat, you should tag it with a standard mapping identifier so the NeuroSignalAssuranceEngine and reporting engine can categorize it correctly against STRIDE or MITRE CWE.

```python
def execute(self, coordinator):
    coordinator.twin.set_clinical_alert(True, "ATTACK-004: Resource Exhaustion Detected")
```

See the [Standards Mapping Registry](validation/standards-mapping.md) for valid threat categories.
