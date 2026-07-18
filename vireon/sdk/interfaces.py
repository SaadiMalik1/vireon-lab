from abc import ABC, abstractmethod
from typing import Any
from vireon.sdk.manifest import CapabilityManifest

class OrchestratorContext:
    """Proxy object given to providers during initialization."""
    def __init__(self, event_bus: Any, state_store: Any):
        self.event_bus = event_bus
        self.state_store = state_store

class IProvider(ABC):
    @property
    @abstractmethod
    def manifest(self) -> CapabilityManifest:
        """Returns the capabilities required by this provider."""
        pass
        
    @abstractmethod
    def initialize(self, context: OrchestratorContext) -> None:
        """Called by the Orchestrator after capabilities are resolved."""
        pass
        
    def on_tick(self, sim_clock: float, dt: float) -> None:
        """Called every simulation tick if the provider subscribes to time."""
        pass
        
    def shutdown(self) -> None:
        """Called during graceful shutdown."""
        pass

class IFirmwareProvider(IProvider):
    @abstractmethod
    def write_memory(self, address: int, data: bytes) -> bool:
        pass
        
    @abstractmethod
    def read_memory(self, address: int, size: int) -> bytes:
        pass
