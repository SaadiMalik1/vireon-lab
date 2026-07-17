from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from vireon.core.event_bus import EventBus, Event

from .base import ISignalModifier
from .engine import SignalAttackEngine

@dataclass
class AttackStep:
    """A single step inside a scripted AttackScenario."""
    time_sec: float
    attack_type: str          # "noise", "drift", "impedance", "suppression"
    duration_sec: float
    target_channels: List[int]
    params: Dict[str, Any] = field(default_factory=dict)
    # Bookkeeping
    _modifier_instance: Optional[ISignalModifier] = None
    _started: bool = False
    _stopped: bool = False


class AttackScenario:
    """A collection of AttackSteps replayed deterministically over the simulation timeline."""

    def __init__(self, name: str, steps: List[AttackStep], event_bus: Optional[EventBus] = None):
        self.name = name
        self.steps = sorted(steps, key=lambda s: s.time_sec)
        self.event_bus = event_bus

    def update(self, sim_clock: float, attack_engine: SignalAttackEngine, registry: Any) -> None:
        """
        Check timeline and active/deactivate scenario steps based on simulation clock.
        """
        for step in self.steps:
            # 1. Trigger steps that should start
            if not step._started and sim_clock >= step.time_sec:
                step._started = True
                try:
                    # Resolve class/factory from PluginRegistry
                    _info = registry.get("attacks", step.attack_type)
                    step._modifier_instance = registry.create(
                        "attacks", step.attack_type,
                        target_channels=step.target_channels,
                        **step.params
                    )
                    attack_engine.add_modifier(step._modifier_instance)

                    if self.event_bus:
                        self.event_bus.publish(Event(
                            topic="attack.scenario_step.started",
                            data={
                                "scenario_name": self.name,
                                "attack_type": step.attack_type,
                                "target_channels": step.target_channels,
                                "duration_sec": step.duration_sec,
                                "sim_clock": sim_clock
                            },
                            source="scenario_player"
                        ))
                except Exception as e:
                    import sys
                    print(f"[AttackScenario] Error starting step: {e}", file=sys.stderr)

            # 2. Reclaim steps that have expired
            if step._started and not step._stopped and sim_clock >= (step.time_sec + step.duration_sec):
                step._stopped = True
                if step._modifier_instance:
                    attack_engine.remove_modifier(step._modifier_instance)

                    if self.event_bus:
                        self.event_bus.publish(Event(
                            topic="attack.scenario_step.stopped",
                            data={
                                "scenario_name": self.name,
                                "attack_type": step.attack_type,
                                "sim_clock": sim_clock
                            },
                            source="scenario_player"
                        ))

