from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from vireon.core.twin import DigitalTwin
from vireon.core.event_bus import EventBus

class VireonPluginSDK(ABC):
    """
    Standard Software Development Kit (SDK) for VIREON Plugins.
    All custom plugins (firmware emulators, external HIL connectors, custom threat models)
    should inherit from this base class to ensure API stability and lifecycle compatibility.
    """

    def __init__(self, name: str, version: str, description: str):
        self.name = name
        self.version = version
        self.description = description
        self.twin: Optional[DigitalTwin] = None
        self.event_bus: Optional[EventBus] = None
        self._is_running = False

    def initialize(self, twin: DigitalTwin, event_bus: EventBus) -> None:
        """
        Inject core platform dependencies into the plugin.
        Called by the Coordinator during plugin loading.
        """
        self.twin = twin
        self.event_bus = event_bus

    @abstractmethod
    def start(self) -> None:
        """
        Start the plugin's execution loop or background threads.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Gracefully stop the plugin and release resources.
        """
        pass

    def is_running(self) -> bool:
        """Return the current running status of the plugin."""
        return self._is_running

    def get_metadata(self) -> Dict[str, Any]:
        """Return standard plugin metadata for the dashboard registry."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "running": self.is_running()
        }
