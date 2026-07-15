"""
Example showing how to create and register a custom VIREON attack plugin.
"""
from vireon.core.attack import BaseAttack

class CustomBatteryDrainAttack(BaseAttack):
    def __init__(self, target_twin, drain_rate=50.0):
        super().__init__(target_twin)
        self.drain_rate = drain_rate

    def apply(self, client, link):
        print(f"Applying custom battery drain attack with rate {self.drain_rate}...")
        link.inject_malformed_packet(b"DRAIN_MAX")
        print("Attack payload delivered.")

def get_plugin_info():
    """
    Entry point for the plugin system.
    """
    return {
        "name": "CustomBatteryDrain",
        "description": "Drains the battery by flooding the BLE interface",
        "class": CustomBatteryDrainAttack,
        "type": "attack"
    }

if __name__ == "__main__":
    print("This is a VIREON plugin. Register it via pyproject.toml entry-points or load dynamically.")
