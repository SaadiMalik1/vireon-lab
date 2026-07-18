from typing import Dict, Any, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

@dataclass
class Event:
    """An event payload published to the bus."""
    topic: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0  # Simulation clock time (set by publisher)
    source: str = ""        # Component name that published

class IEventBus(ABC):
    """Interface for the publish-subscribe event bus."""
    @abstractmethod
    def subscribe(self, topic: str, handler: Callable[[Event], None], priority: int = 100) -> str:
        """Subscribe a handler to a topic."""
        pass
    
    @abstractmethod
    def unsubscribe(self, sub_id: str) -> bool:
        """Remove a subscription by its ID."""
        pass
    
    @abstractmethod
    def publish(self, event: Event) -> None:
        """Publish an event."""
        pass
