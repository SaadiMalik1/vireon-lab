"""
NeuroShield Plugin Registry — Discovery, Registration, and Factory Management.

Plugins register themselves with a unique name, category, factory,
and optional configuration schema. The registry handles lifecycle
and provides typed access to plugin instances.
"""

from typing import Dict, Any, Optional, List, Type, Callable
from dataclasses import dataclass, field
import threading


@dataclass
class PluginInfo:
    """Metadata describing a registered plugin."""
    name: str
    category: str                # "datasets", "devices", "attacks", "clinical", "reports", "wireless"
    description: str = ""
    factory: Optional[Callable] = None   # Callable that creates an instance
    plugin_class: Optional[Type] = None  # Or a class to instantiate
    version: str = "0.0.0"
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)


class PluginRegistry:
    """
    Central registry for all NeuroShield plugins.

    Plugins register via `register()` and are retrieved via `get()` or `create()`.
    The registry ensures no duplicate names within a category and provides
    discovery methods for listing available plugins.

    Usage:
        registry = PluginRegistry()
        registry.register(PluginInfo(
            name="edf_reader",
            category="datasets",
            description="European Data Format reader",
            plugin_class=EDFReader
        ))

        reader_class = registry.get("datasets", "edf_reader").plugin_class
        reader = registry.create("datasets", "edf_reader", file_path="data.edf")
    """

    def __init__(self):
        self._plugins: Dict[str, Dict[str, PluginInfo]] = {}
        self._lock = threading.Lock()

    def register(self, info: PluginInfo) -> None:
        """
        Register a plugin.

        Args:
            info: PluginInfo with at minimum name, category, and either
                  factory or plugin_class.

        Raises:
            ValueError: If a plugin with the same name is already registered
                        in the same category.
        """
        with self._lock:
            if info.category not in self._plugins:
                self._plugins[info.category] = {}

            if info.name in self._plugins[info.category]:
                raise ValueError(
                    f"Plugin '{info.name}' already registered in category '{info.category}'"
                )

            self._plugins[info.category][info.name] = info

    def unregister(self, category: str, name: str) -> bool:
        """Remove a plugin registration. Returns True if found and removed."""
        with self._lock:
            if category in self._plugins and name in self._plugins[category]:
                del self._plugins[category][name]
                return True
        return False

    def get(self, category: str, name: str) -> PluginInfo:
        """
        Retrieve plugin metadata.

        Raises:
            KeyError: If the plugin is not found.
        """
        with self._lock:
            if category not in self._plugins or name not in self._plugins[category]:
                raise KeyError(f"Plugin '{name}' not found in category '{category}'")
            return self._plugins[category][name]

    def create(self, category: str, name: str, **kwargs) -> Any:
        """
        Create a plugin instance using its factory or class constructor.

        Args:
            category: Plugin category.
            name: Plugin name.
            **kwargs: Arguments passed to the factory/constructor.

        Returns:
            A new plugin instance.

        Raises:
            KeyError: If the plugin is not found.
            ValueError: If the plugin has no factory or class.
        """
        info = self.get(category, name)

        if info.factory is not None:
            return info.factory(**kwargs)
        elif info.plugin_class is not None:
            return info.plugin_class(**kwargs)
        else:
            raise ValueError(
                f"Plugin '{name}' in '{category}' has no factory or class to instantiate"
            )

    def list_category(self, category: str) -> List[PluginInfo]:
        """List all plugins in a category."""
        with self._lock:
            if category not in self._plugins:
                return []
            return list(self._plugins[category].values())

    def list_categories(self) -> List[str]:
        """List all registered categories."""
        with self._lock:
            return list(self._plugins.keys())

    def list_all(self) -> Dict[str, List[PluginInfo]]:
        """Return all plugins grouped by category."""
        with self._lock:
            return {
                cat: list(plugins.values())
                for cat, plugins in self._plugins.items()
            }

    def has(self, category: str, name: str) -> bool:
        """Check if a plugin is registered."""
        with self._lock:
            return (category in self._plugins and
                    name in self._plugins[category])

    def clear(self):
        """Remove all registrations. Used in testing."""
        with self._lock:
            self._plugins.clear()

    def load_entry_points(self):
        """Discover and load external plugins via Python entry points."""
        import importlib.metadata
        import os
        import json
        
        try:
            # Python 3.10+ way
            eps = importlib.metadata.entry_points(group="neuroshield.plugins")
        except TypeError:
            # Fallback for Python 3.9
            eps = importlib.metadata.entry_points().get("neuroshield.plugins", [])
            
        # Load user opt-in configuration if it exists
        user_allowed = []
        if os.path.exists("plugins.json"):
            try:
                with open("plugins.json", "r") as f:
                    config = json.load(f)
                    user_allowed = config.get("allowed_plugins", [])
            except Exception as e:
                print(f"[PluginRegistry] Failed to parse plugins.json: {e}")

        for ep in eps:
            try:
                # Security check: whitelist allowed modules
                allowed_prefixes = (
                    "neuroshield.plugins.datasets.",
                    "neuroshield.plugins.devices.",
                    "neuroshield.plugins.clinical.",
                    "neuroshield.plugins.reports.",
                    "neuroshield.plugins.attacks."
                )
                
                is_builtin = ep.value.startswith(allowed_prefixes)
                is_opted_in = any(ep.value.startswith(prefix) for prefix in user_allowed)
                
                if not (is_builtin or is_opted_in):
                    print(f"[PluginRegistry] SECURITY ALERT: Blocked untrusted external plugin '{ep.name}' from module '{ep.value}'. To allow, add to plugins.json.")
                    continue
                    
                plugin_info_loader = ep.load()
                # loader should return a PluginInfo or list of PluginInfo
                info = plugin_info_loader()
                if isinstance(info, list):
                    for i in info:
                        self.register(i)
                else:
                    self.register(info)
                print(f"[PluginRegistry] Loaded external plugin: {ep.name}")
            except Exception as e:
                print(f"[PluginRegistry] Failed to load plugin {ep.name}: {e}")

def register_builtin_plugins(registry: PluginRegistry) -> None:
    """
    Register all built-in NeuroShield plugins.

    This is called during Coordinator initialization to make all
    shipped components available through the registry.
    """
    # --- Dataset Readers ---
    from neuroshield.plugins.datasets.edf_reader import EDFReader
    from neuroshield.plugins.datasets.mock_reader import MockEEGReader
    from neuroshield.plugins.datasets.csv_reader import CSVReader
    from neuroshield.plugins.datasets.fif_reader import FIFReader

    registry.register(PluginInfo(
        name="edf_reader",
        category="datasets",
        description="European Data Format (EDF/BDF) file reader",
        plugin_class=EDFReader,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="csv_reader",
        category="datasets",
        description="CSV EEG data reader",
        plugin_class=CSVReader,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="fif_reader",
        category="datasets",
        description="MNE Functional Imaging File (.fif) reader",
        plugin_class=FIFReader,
        version="1.0.0"
    ))
    
    from neuroshield.plugins.datasets.mne_reader import MNEReader
    registry.register(PluginInfo(
        name="mne_reader",
        category="datasets",
        description="MNE Universal Reader (vhdr, set, edf, bdf, fif)",
        plugin_class=MNEReader,
        version="1.0.0"
    ))
    
    registry.register(PluginInfo(
        name="mock_eeg",
        category="datasets",
        description="Synthetic multi-band EEG signal generator (alpha/beta/gamma/delta)",
        plugin_class=MockEEGReader,
        version="1.0.0"
    ))
    
    from neuroshield.plugins.datasets.eeg_sample_reader import EEGSampleReader
    registry.register(PluginInfo(
        name="eeg_sample",
        category="datasets",
        description="Reads dataset metadata from datalake eeg-samples.json",
        plugin_class=EEGSampleReader,
        version="1.0.0"
    ))

    # --- Device Wrappers ---
    from neuroshield.plugins.devices.synthetic import SyntheticBoardWrapper
    from neuroshield.plugins.devices.pieeg import PiEEGBoardWrapper
    from neuroshield.plugins.devices.openbci_board import OpenBCICytonWrapper, OpenBCIGanglionWrapper
    from neuroshield.plugins.devices.muse_emulator import MuseEmulator
    from neuroshield.plugins.devices.emotiv_emulator import EmotivEpocEmulator

    registry.register(PluginInfo(
        name="synthetic",
        category="devices",
        description="BrainFlow Synthetic Board (or mock fallback)",
        plugin_class=SyntheticBoardWrapper,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="pieeg",
        category="devices",
        description="PiEEG Raspberry Pi SPI Board (or mock fallback)",
        plugin_class=PiEEGBoardWrapper,
        version="1.0.0"
    ))
    
    registry.register(PluginInfo(
        name="cyton",
        category="devices",
        description="Physical OpenBCI Cyton Board (via BrainFlow)",
        plugin_class=OpenBCICytonWrapper,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="ganglion",
        category="devices",
        description="Physical OpenBCI Ganglion Board (via BrainFlow)",
        plugin_class=OpenBCIGanglionWrapper,
        version="1.0.0"
    ))
    
    from neuroshield.plugins.devices.lsl_bridge import LSLDeviceWrapper
    registry.register(PluginInfo(
        name="lsl",
        category="devices",
        description="Lab Streaming Layer (LSL) Inlet Wrapper",
        plugin_class=LSLDeviceWrapper,
        version="1.0.0"
    ))
    
    registry.register(PluginInfo(
        name="muse",
        category="devices",
        description="Muse Headset Emulator (4-channel)",
        plugin_class=MuseEmulator,
        version="1.0.0"
    ))
    
    registry.register(PluginInfo(
        name="emotiv",
        category="devices",
        description="Emotiv Epoc+ Headset Emulator (14-channel)",
        plugin_class=EmotivEpocEmulator,
        version="1.0.0"
    ))

    # --- Attack Modifiers ---
    from neuroshield.core.attack import (
        NoiseInjectionAttack, SignalDriftAttack,
        ImpedanceSpikeAttack, SignalSuppressionAttack
    )

    registry.register(PluginInfo(
        name="noise",
        category="attacks",
        description="Gaussian noise injection attack",
        plugin_class=NoiseInjectionAttack,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="drift",
        category="attacks",
        description="Signal baseline drift attack",
        plugin_class=SignalDriftAttack,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="impedance",
        category="attacks",
        description="Electrode impedance spike / disconnection attack",
        plugin_class=ImpedanceSpikeAttack,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="suppression",
        category="attacks",
        description="Signal attenuation / suppression attack",
        plugin_class=SignalSuppressionAttack,
        version="1.0.0"
    ))

    # --- Clinical ---
    from neuroshield.plugins.clinical.closed_loop import ClosedLoopSimulator
    from neuroshield.plugins.clinical.dbs_emulator import ClosedLoopDBSController

    registry.register(PluginInfo(
        name="closed_loop",
        category="clinical",
        description="Closed-loop clinical simulation evaluator",
        plugin_class=ClosedLoopSimulator,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="dbs_controller",
        category="clinical",
        description="Closed-loop Deep Brain Stimulation controller",
        plugin_class=ClosedLoopDBSController,
        version="1.0.0"
    ))
