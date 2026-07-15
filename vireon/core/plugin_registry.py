"""
VIREON Plugin Registry — Discovery, Registration, and Factory Management.

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
    category: str                # "datasets", "devices", "attacks", "clinical", "reports", "wireless", "security"
    description: str = ""
    factory: Optional[Callable] = None   # Callable that creates an instance
    plugin_class: Optional[Type] = None  # Or a class to instantiate
    version: str = "0.0.0"
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)


class PluginRegistry:
    """
    Central registry for all VIREON plugins.

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
            eps = importlib.metadata.entry_points(group="vireon.plugins")
        except TypeError:
            # Fallback for Python 3.9
            eps = importlib.metadata.entry_points().get("vireon.plugins", [])
            
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
                    "vireon.plugins.datasets.",
                    "vireon.plugins.devices.",
                    "vireon.plugins.clinical.",
                    "vireon.plugins.reports.",
                    "vireon.plugins.attacks."
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
    Register all built-in VIREON plugins.
    First tries to use importlib.metadata entry points for dynamic discovery.
    Falls back to hardcoded registrations for backward compatibility.
    """
    import importlib.metadata
    import logging
    logger = logging.getLogger(__name__)

    # 1. Dynamic Discovery via entry_points
    try:
        eps = importlib.metadata.entry_points()
        if hasattr(eps, 'select'):
            vireon_eps = eps.select(group='vireon.plugins')
        else:
            vireon_eps = eps.get('vireon.plugins', []) # type: ignore
        
        for ep in vireon_eps:
            try:
                plugin_loader = ep.load()
                info = plugin_loader()
                if isinstance(info, list):
                    for i in info:
                        if not registry.has(i.category, i.name):
                            registry.register(i)
                else:
                    if not registry.has(info.category, info.name):
                        registry.register(info)
            except Exception as e:
                logger.error(f"[PluginRegistry] Failed to dynamically load plugin {ep.name}: {e}")
    except Exception as e:
        logger.warning(f"[PluginRegistry] Entry point discovery failed: {e}")

    # 2. Fallback to manual registration
    from vireon.plugins.datasets.edf_reader import EDFReader
    from vireon.plugins.datasets.mock_reader import MockEEGReader
    from vireon.plugins.datasets.csv_reader import CSVReader
    from vireon.plugins.datasets.fif_reader import FIFReader

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
    
    from vireon.plugins.datasets.mne_reader import MNEReader
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
    
    from vireon.plugins.datasets.eeg_sample_reader import EEGSampleReader
    registry.register(PluginInfo(
        name="eeg_sample",
        category="datasets",
        description="Reads dataset metadata from datalake eeg-samples.json",
        plugin_class=EEGSampleReader,
        version="1.0.0"
    ))

    # --- Device Wrappers ---
    from vireon.plugins.devices.synthetic import SyntheticBoardWrapper
    from vireon.plugins.devices.pieeg import PiEEGBoardWrapper
    from vireon.plugins.devices.openbci_board import OpenBCICytonWrapper, OpenBCIGanglionWrapper
    from vireon.plugins.devices.muse_emulator import MuseEmulator
    from vireon.plugins.devices.emotiv_emulator import EmotivEpocEmulator

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
    
    from vireon.plugins.devices.lsl_bridge import LSLDeviceWrapper
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
    from vireon.core.attack import (
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

    try:
        from vireon.attacks.adversarial_ml import (
            FGSMAttack, PGDAttack, CWAttack, BackdoorTriggerInjector
        )
        registry.register(PluginInfo(
            name="fgsm",
            category="attacks",
            description="Fast Gradient Sign Method adversarial noise",
            plugin_class=FGSMAttack,
            version="1.0.0"
        ))
        registry.register(PluginInfo(
            name="pgd",
            category="attacks",
            description="Projected Gradient Descent adversarial attack",
            plugin_class=PGDAttack,
            version="1.0.0"
        ))
        registry.register(PluginInfo(
            name="cw",
            category="attacks",
            description="Carlini & Wagner targeted frequency injection",
            plugin_class=CWAttack,
            version="1.0.0"
        ))
        registry.register(PluginInfo(
            name="backdoor",
            category="attacks",
            description="Training-time data poisoning trigger injection",
            plugin_class=BackdoorTriggerInjector,
            version="1.0.0"
        ))
    except ImportError as e:
        print(f"[PluginRegistry] Skipping adversarial_ml attacks: {e}")

    # --- Clinical ---
    from vireon.plugins.clinical.closed_loop import ClosedLoopSimulator
    from vireon.plugins.clinical.dbs_emulator import ClosedLoopDBSController

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

    # --- Security & Privacy ---
    from vireon.core.detection import SecurityEngine
    from vireon.core.clinical import NeuroIPS, BLELinkGuard
    from vireon.plugins.firmware.cortex_m_stub import FirmwareSecurityMonitor
    from vireon.core.privacy_leakage import P300Analyzer
    from vireon.core.e2ee import E2EEChannel
    from vireon.core.authentication import BiometricGate
    from vireon.core.zta import ZTAPolicyEngine
    from vireon.core.threat_intel import ThreatIntelligence

    registry.register(PluginInfo(
        name="ids",
        category="security",
        description="Intrusion Detection System for neural anomalies",
        plugin_class=SecurityEngine,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="ips",
        category="security",
        description="Intrusion Prevention System for neural anomalies",
        plugin_class=NeuroIPS,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="ble_guard",
        category="security",
        description="Bluetooth Low Energy protocol monitor",
        plugin_class=BLELinkGuard,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="fw_monitor",
        category="security",
        description="Firmware execution environment monitor",
        plugin_class=FirmwareSecurityMonitor,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="p300_analyzer",
        category="security",
        description="Privacy leakage analyzer for P300 potentials",
        plugin_class=P300Analyzer,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="e2ee_channel",
        category="security",
        description="End-to-end encrypted channel wrapper",
        plugin_class=E2EEChannel,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="biometric_gate",
        category="security",
        description="Neuro-biometric authentication gate",
        plugin_class=BiometricGate,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="zta_engine",
        category="security",
        description="Zero-Trust Architecture policy engine",
        plugin_class=ZTAPolicyEngine,
        version="1.0.0"
    ))
    registry.register(PluginInfo(
        name="threat_intel",
        category="security",
        description="Threat Intelligence mapping",
        plugin_class=ThreatIntelligence,
        version="1.0.0"
    ))
