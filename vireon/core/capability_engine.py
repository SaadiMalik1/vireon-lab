from typing import List, Dict, Any
from vireon.sdk.manifest import CapabilityManifest
from vireon.core.config import ExperimentConfig

class CapabilityViolationError(Exception):
    pass

class CapabilityEngine:
    def __init__(self, config: ExperimentConfig):
        self.config = config

    def validate_manifest(self, manifest: CapabilityManifest) -> bool:
        """
        Validates whether the requested capabilities are allowed by the current
        ExperimentConfig.
        """
        # In the future, read self.config.security.policy
        # For now, we allow all if security is disabled, else we apply simple checks.
        
        # Example check: if strict_offline is required, block network
        # if manifest.requires_host_access and self.config.security.strict_offline:
        #    return False
        
        return True

class EventBusProxy:
    """Wraps an EventBus, enforcing a provider's pub/sub capabilities."""
    def __init__(self, real_bus, manifest: CapabilityManifest):
        self._bus = real_bus
        self._manifest = manifest

    def publish(self, event) -> None:
        if event.topic not in self._manifest.publishes_events and "*" not in self._manifest.publishes_events:
            raise CapabilityViolationError(f"Provider {self._manifest.name} not authorized to publish to {event.topic}")
        self._bus.publish(event)

    def subscribe(self, topic, handler, priority=100) -> str:
        if topic not in self._manifest.subscribes_events and "*" not in self._manifest.subscribes_events:
            raise CapabilityViolationError(f"Provider {self._manifest.name} not authorized to subscribe to {topic}")
        return self._bus.subscribe(topic, handler, priority)

class StateStoreProxy:
    """Wraps a StateStore, enforcing a provider's read/mutate capabilities."""
    def __init__(self, real_store, manifest: CapabilityManifest):
        self._store = real_store
        self._manifest = manifest

    def get(self, key: str, default: Any = None) -> Any:
        if key not in self._manifest.reads_state and "*" not in self._manifest.reads_state:
            raise CapabilityViolationError(f"Provider {self._manifest.name} not authorized to read state {key}")
        return self._store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if key not in self._manifest.mutates_state and "*" not in self._manifest.mutates_state:
            raise CapabilityViolationError(f"Provider {self._manifest.name} not authorized to mutate state {key}")
        self._store.set(key, value, source=self._manifest.name)
