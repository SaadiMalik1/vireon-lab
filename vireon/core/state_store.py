import threading
from typing import Any, Dict, Optional
from vireon.core.event_bus import EventBus, Event

class StateStore:
    """
    Central, thread-safe Key-Value store replacing the DigitalTwin God-class.
    All state mutations are broadcast over the EventBus.
    """
    def __init__(self, event_bus: EventBus):
        self._state: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self.event_bus = event_bus

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._state.get(key, default)

    def set(self, key: str, value: Any, source: str = "system") -> None:
        with self._lock:
            old_value = self._state.get(key)
            if old_value != value:
                self._state[key] = value
                self.event_bus.publish(Event(
                    topic=f"state.changed.{key}",
                    data={"old": old_value, "new": value},
                    source=source
                ))

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._state)
