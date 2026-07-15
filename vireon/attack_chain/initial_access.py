from typing import Dict, Any
from .base import AttackStage

class InitialAccessStage(AttackStage):
    def execute(self, context: Dict[str, Any]) -> bool:
        self.active = True
        self.event_bus.publish("attack.initial_access.start", {"capability": self.capability.value})
        
        # Requires at least L1 (Radio attacker) or higher
        if self.capability.value >= "L1":
            context["initial_access"] = True
            self.event_bus.publish("attack.initial_access.success", {})
            return True
        
        self.event_bus.publish("attack.initial_access.failed", {"reason": "Insufficient capability"})
        return False
