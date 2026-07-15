# Tutorial 2: Creating a Custom Attack

In this tutorial, you will create a custom attack plugin.

## 1. Subclass BaseAttack
Create a file `my_attack.py`:
```python
from vireon.core.attack import BaseAttack

class BatteryDrainAttack(BaseAttack):
    def apply(self, client, link):
        # Force the implant to max amplitude
        link.inject_malformed_packet(b"SET_AMP_MAX")
```

## 2. Registering the Attack
Load this attack in your `default.toml` or explicitly in `main.py`:
```python
attack = BatteryDrainAttack(coordinator.twin)
attack.apply(coordinator.ble_client, coordinator.ble_link)
```

## 3. Run and Monitor
Run the simulation and use `vireon ui` to watch the battery level drop rapidly.
