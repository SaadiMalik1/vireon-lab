"""
VIREON Event Bus — Publish/Subscribe System for Decoupled Component Communication.

All subsystems communicate through this bus instead of direct method calls.
Topics use dot-notation namespacing:
    signal.chunk_ready
    ids.anomaly_detected
    ips.attack_blocked
    twin.state_changed
    experiment.started
    experiment.stopped
    attack.injected
    attack.scenario_step
"""

import threading
import uuid
import concurrent.futures
from collections import deque
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Event:
    """An event payload published to the bus."""
    topic: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0  # Simulation clock time (set by publisher)
    source: str = ""        # Component name that published


@dataclass
class _Subscription:
    sub_id: str
    topic: str
    handler: Callable[[Event], None]
    priority: int  # Lower = fires first


class EventBus:
    """
    Synchronous publish-subscribe event bus.

    Handlers are invoked synchronously in priority order within the simulation
    thread. This avoids threading complexity while keeping components decoupled.

    Usage:
        bus = EventBus()
        sub_id = bus.subscribe("ids.anomaly_detected", my_handler)
        bus.publish(Event(topic="ids.anomaly_detected", data={"type": "HIGH_NOISE"}))
        bus.unsubscribe(sub_id)
    """

    def __init__(self):
        self._subscriptions: Dict[str, List[_Subscription]] = {}
        self._lock = threading.Lock()
        self._event_log: deque = deque(maxlen=10000)
        self._dead_letters: List[Dict[str, Any]] = []
        self._log_enabled = False
        self._max_log_size = 10000
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=10, thread_name_prefix="EventBus-")

    def subscribe(self, topic: str, handler: Callable[[Event], None],
                  priority: int = 100) -> str:
        """
        Subscribe a handler to a topic.

        Args:
            topic: Dot-notation event topic (e.g., "ids.anomaly_detected").
                   Use "*" to subscribe to all events.
            handler: Callable that receives an Event object.
            priority: Lower values fire first. Default 100.

        Returns:
            Subscription ID (for later unsubscription).
        """
        sub_id = str(uuid.uuid4())
        sub = _Subscription(sub_id=sub_id, topic=topic, handler=handler, priority=priority)

        with self._lock:
            if topic not in self._subscriptions:
                self._subscriptions[topic] = []
            self._subscriptions[topic].append(sub)
            # Keep sorted by priority
            self._subscriptions[topic].sort(key=lambda s: s.priority)

        return sub_id

    def unsubscribe(self, sub_id: str) -> bool:
        """Remove a subscription by its ID. Returns True if found and removed."""
        with self._lock:
            for topic, subs in self._subscriptions.items():
                for i, sub in enumerate(subs):
                    if sub.sub_id == sub_id:
                        subs.pop(i)
                        return True
        return False

    def publish(self, event: Event) -> None:
        """
        Publish an event. All matching handlers are dispatched asynchronously
        in priority order.
        """
        if self._log_enabled:
            with self._lock:
                self._event_log.append(event)

        # Collect handlers to invoke (snapshot under lock to avoid mutation during iteration)
        handlers_to_call: List[Callable[[Event], None]] = []
        with self._lock:
            # Topic-specific subscribers
            if event.topic in self._subscriptions:
                for sub in self._subscriptions[event.topic]:
                    handlers_to_call.append(sub.handler)
            # Wildcard subscribers
            if "*" in self._subscriptions:
                for sub in self._subscriptions["*"]:
                    handlers_to_call.append(sub.handler)

        # Invoke asynchronously outside lock
        def _run_handler(h, e):
            try:
                h(e)
            except Exception as ex:
                import sys
                import traceback
                print(f"[EventBus] Handler error on '{e.topic}': {ex}", file=sys.stderr)
                with self._lock:
                    self._dead_letters.append({
                        "event": e,
                        "error": str(ex),
                        "handler": getattr(h, "__name__", str(h)),
                        "traceback": traceback.format_exc()
                    })

        for handler in handlers_to_call:
            self._executor.submit(_run_handler, handler, event)

    def get_dead_letters(self) -> List[Dict[str, Any]]:
        """Return all failed events (dead-letter queue)."""
        with self._lock:
            return list(self._dead_letters)
            
    def clear_dead_letters(self):
        """Clear the dead-letter queue."""
        with self._lock:
            self._dead_letters.clear()
            
    def enable_logging(self, enabled: bool = True, max_size: int = 10000):
        """Enable/disable event logging for debugging and replay."""
        with self._lock:
            self._log_enabled = enabled
            if max_size != self._max_log_size:
                self._max_log_size = max_size
                old_events = list(self._event_log)
                self._event_log = deque(old_events, maxlen=self._max_log_size)

    def get_event_log(self) -> List[Event]:
        """Return a copy of the event log."""
        with self._lock:
            return list(self._event_log)

    def clear_event_log(self):
        """Clear the event log."""
        with self._lock:
            self._event_log.clear()

    def get_subscriber_count(self, topic: Optional[str] = None) -> int:
        """Return the number of subscribers, optionally filtered by topic."""
        with self._lock:
            if topic is not None:
                return len(self._subscriptions.get(topic, []))
            return sum(len(subs) for subs in self._subscriptions.values())

    def clear(self):
        """Remove all subscriptions and logs. Used in testing."""
        with self._lock:
            self._subscriptions.clear()
            self._event_log.clear()

    def flush(self):
        """Wait for all currently queued handlers to finish executing."""
        futures = [self._executor.submit(lambda: None) for _ in range(self._executor._max_workers)]
        concurrent.futures.wait(futures)
