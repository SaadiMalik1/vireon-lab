import numpy as np
from typing import List, Optional
from vireon.core.twin import DigitalTwin
from vireon.core.event_bus import EventBus, Event

from .base import ISignalModifier

class SignalAttackEngine:
    def __init__(self, twin: DigitalTwin, event_bus: Optional[EventBus] = None):
        self.twin = twin
        self.event_bus = event_bus
        self.modifiers: List[ISignalModifier] = []
        import threading
        self.lock = threading.RLock()

    def add_modifier(self, modifier: ISignalModifier):
        with self.lock:
            self.modifiers.append(modifier)

        if self.event_bus:
            # Extract parameters
            params = {}
            if hasattr(modifier, "noise_level"):
                params["noise_level_uv"] = modifier.noise_level
            elif hasattr(modifier, "drift_rate"):
                params["drift_rate_uv_per_sec"] = modifier.drift_rate
            elif hasattr(modifier, "spike_value"):
                params["spike_value_kohm"] = modifier.spike_value
            elif hasattr(modifier, "attenuation_factor"):
                params["attenuation_factor"] = modifier.attenuation_factor

            self.event_bus.publish(Event(
                topic="attack.modifier_added",
                data={
                    "type": modifier.__class__.__name__,
                    "target_channels": getattr(modifier, "target_channels", []),
                    "params": params,
                    "sim_clock": self.twin.get_sim_clock()
                },
                source="attack_engine"
            ))

    def remove_modifier(self, modifier: ISignalModifier):
        removed = False
        with self.lock:
            if modifier in self.modifiers:
                self.modifiers.remove(modifier)
                removed = True

        if removed:
            modifier.revert(self.twin)

        if removed and self.event_bus:
            self.event_bus.publish(Event(
                topic="attack.modifier_removed",
                data={
                    "type": modifier.__class__.__name__,
                    "sim_clock": self.twin.get_sim_clock()
                },
                source="attack_engine"
            ))

    def apply_attacks(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        processed_data = data.copy()
        with self.lock:
            active_mods = list(self.modifiers)

        # Reset twin-level properties that might have been left over
        setattr(self.twin, "rf_packet_drop_rate", 0.0)

        for modifier in active_mods:
            processed_data = modifier.apply(processed_data, eeg_channels, sample_rate, self.twin, rng)

        if active_mods and self.event_bus:
            self.event_bus.publish(Event(
                topic="attack.applied",
                data={
                    "active_modifiers_count": len(active_mods),
                    "sim_clock": self.twin.get_sim_clock()
                },
                source="attack_engine"
            ))

        return processed_data

