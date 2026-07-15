from abc import ABC, abstractmethod
from typing import Dict, Any
from vireon.core.config import AttackerCapability
from vireon.core.event_bus import EventBus

class AttackStage(ABC):
    """Base class for all stages in the attack lifecycle."""
    
    def __init__(self, capability: AttackerCapability, event_bus: EventBus):
        self.capability = capability
        self.event_bus = event_bus
        self.active = False
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute this stage. 
        Returns True if successful and the attack chain can proceed to the next stage.
        """
        pass
