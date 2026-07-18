from typing import Any, Dict
from abc import ABC, abstractmethod
from vireon.sdk.events import IEventBus

class IStateStore(ABC):
    """Interface for the central State Store."""
    event_bus: IEventBus
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, source: str = "system") -> None:
        pass

    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        pass
