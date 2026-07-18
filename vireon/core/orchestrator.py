import time
import sys
import threading
import logging
from typing import Optional

from vireon.core.event_bus import EventBus, Event
from vireon.core.config import ExperimentConfig
from vireon.core.plugin_registry import PluginRegistry, register_builtin_plugins
from vireon.core.capability_engine import CapabilityEngine
from vireon.core.state_store import StateStore
from vireon.core.engine import ReplayEngine
from vireon.core.utils import format_telemetry_table

# Compatibility imports for plugins not yet refactored to IProvider
from vireon.core.twin import DigitalTwin
from vireon.core.coordinator_builder import SimulationBuilder

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Thin Orchestration Runtime for VIREON.
    Replaces the monolithic Coordinator. Orchestrates Provider interfaces based on
    a capability-negotiated manifest.
    """

    def __init__(self, config: ExperimentConfig):
        self.config = config

        # Thin Runtime Core
        self.event_bus = EventBus()
        self.registry = PluginRegistry()
        self.capability_engine = CapabilityEngine(config)
        self.state_store = StateStore(self.event_bus)

        self.engine: Optional[ReplayEngine] = None
        self._setup_complete = False

        # --- BACKWARD COMPATIBILITY SHIM ---
        # Plugins have not yet been migrated to IProvider and StateStore.
        # We temporarily maintain DigitalTwin and specific references.
        self.twin: Optional[DigitalTwin] = None
        self.attack_engine = None
        self.clinical_sim = None
        self.dbs_controller = None
        self.emulator = None
        self.fw_monitor = None
        self.ids = None
        self.ips = None
        self.link_guard = None
        self.p300_analyzer = None
        self.e2ee_channel = None
        self.biometric_gate = None
        self.zta_engine = None
        self.bridge = None
        self.web_server = None
        self.ws_server = None

    def setup(self):
        print("[VIREON Orchestrator] Bootstrapping Thin Runtime...")

        # 1. Discover plugins
        register_builtin_plugins(self.registry)
        self.registry.load_entry_points()

        # 2. Provide backward compatibility
        self._setup_legacy_plugins()

        self.event_bus.publish(Event(
            topic="experiment.setup_complete",
            data={"config_name": self.config.name, "seed": self.config.seed},
            source="orchestrator"
        ))
        self._setup_complete = True

    def _setup_legacy_plugins(self):
        """Temporary shim to load old plugins until Phase 9 Subsystem 3 completes."""
        self.twin = DigitalTwin(
            device_id=self.config.device.device_id,
            sample_rate=self.config.device.sample_rate,
            num_channels=self.config.device.num_channels,
            hardware_mode=self.config.emulation.hardware_loopback,
            seed=self.config.seed
        )
        
        # We put the twin in the StateStore so new providers can access it if needed
        self.state_store.set("legacy_twin", self.twin, source="orchestrator")

        from vireon.core.attack import SignalAttackEngine
        self.attack_engine = SignalAttackEngine(self.twin, self.event_bus)
        self.event_bus.enable_logging(True)

        builder = SimulationBuilder(self)
        builder.setup_attacks()

        device_wrapper = builder.setup_device()
        dataset_reader = builder.setup_dataset()

        from vireon.core.data_provider import DeviceProviderAdapter, DatasetProviderAdapter
        provider = None
        if device_wrapper:
            provider = DeviceProviderAdapter(device_wrapper)
        elif dataset_reader:
            provider = DatasetProviderAdapter(dataset_reader)

        self.engine = ReplayEngine(
            state_store=self.state_store,
            attack_engine=self.attack_engine,
            provider=provider,
            seed=self.config.seed,
            loop_dataset=self.config.dataset.loop
        )

        from vireon.plugins.clinical.closed_loop import ClosedLoopSimulator
        self.clinical_sim = ClosedLoopSimulator(self.twin)
        
        from vireon.core.coordinator_callbacks import CoordinatorCallbacks
        self.callbacks = CoordinatorCallbacks(self)
        self.engine.add_callback(self.callbacks.simulation_callback)

    def run(self):
        if not self._setup_complete:
            raise RuntimeError("Call setup() before run()")

        self.event_bus.publish(Event(
            topic="experiment.started",
            data={"duration": self.config.duration_sec},
            source="orchestrator"
        ))

        print(f"[VIREON Orchestrator] Starting simulation (duration={self.config.duration_sec}s)...")
        self.engine.start(interval_sec=self.config.interval_sec)
        start_time = time.time()

        try:
            while time.time() - start_time < self.config.duration_sec:
                if not self.config.web.enabled:
                    sys.stdout.write("\033[H\033[J")
                    sys.stdout.write(format_telemetry_table(self.twin))
                    sys.stdout.write(f"\nSim Clock: {self.engine.sim_clock:.1f}s | Speed: {self.engine.speed:.1f}x\n")
                    sys.stdout.flush()
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[VIREON] Simulation interrupted by user.")

        self.event_bus.publish(Event(
            topic="experiment.stopped",
            data={"sim_clock": self.engine.sim_clock},
            source="orchestrator"
        ))

    def teardown(self):
        print("\n[VIREON] Stopping replay engine...")
        if self.engine:
            self.engine.stop()
