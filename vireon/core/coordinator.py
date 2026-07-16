"""
VIREON Coordinator — Central orchestrator for the simulation pipeline.

Replaces the monolithic main() function with a properly structured class
that can be used both programmatically and from the CLI.
"""

import time
import sys
import threading
import logging
from typing import Optional, Any

from vireon.core.twin import DigitalTwin
from vireon.core.engine import ReplayEngine
from vireon.core.attack import SignalAttackEngine
from vireon.core.event_bus import EventBus, Event
from vireon.core.config import ExperimentConfig
from vireon.core.plugin_registry import PluginRegistry, register_builtin_plugins
from vireon.core.utils import format_telemetry_table
from vireon.plugins.clinical.closed_loop import ClosedLoopSimulator

logger = logging.getLogger(__name__)
class Coordinator:
    """
    Orchestrates a VIREON simulation experiment.

    Responsibilities:
    1. Initialize core components (Twin, EventBus, Registry)
    2. Configure the pipeline from an ExperimentConfig
    3. Wire event subscriptions between components
    4. Run the simulation loop
    5. Handle graceful shutdown and report compilation

    Usage:
        config = load_config("experiment.toml")
        coordinator = Coordinator(config)
        coordinator.setup()
        coordinator.run()  # Blocks until duration elapsed or Ctrl+C
        coordinator.teardown()
    """

    def __init__(self, config: ExperimentConfig):
        self.config = config

        # Core components
        self.event_bus = EventBus()
        self.registry = PluginRegistry()
        self.twin: Optional[DigitalTwin] = None
        self.attack_engine: Optional[SignalAttackEngine] = None
        self.engine: Optional[ReplayEngine] = None
        self.lock = threading.Lock()

        # Optional components (initialized during setup based on config)
        self.clinical_sim: Optional[ClosedLoopSimulator] = None
        self.dbs_controller: Optional[Any] = None
        self.ids: Optional[Any] = None
        self.ips: Optional[Any] = None
        self.link_guard: Optional[Any] = None
        self.emulator: Optional[Any] = None
        self.fw_monitor: Optional[Any] = None
        self.ble_server: Optional[Any] = None
        self.p300_analyzer: Optional[Any] = None
        self.total_p300_leakage_events: int = 0
        self.e2ee_channel: Optional[Any] = None
        self.biometric_gate: Optional[Any] = None
        self.ble_link: Optional[Any] = None
        self.ble_client: Optional[Any] = None
        self.bridge: Optional[Any] = None
        self.web_server: Optional[Any] = None
        self.ws_server: Optional[Any] = None
        self.lsl_streamer: Optional[Any] = None
        self.threat_intel: Optional[Any] = None
        self.nsp_wrapper: Optional[Any] = None
        self.zta_engine: Optional[Any] = None

        self._setup_complete = False

    def setup(self):
        """Initialize all components based on config. Call once before run()."""
        print("[VIREON] Initializing Virtual Laboratory...")
        
        # 0. Enforce Neuroethics Guardrails
        try:
            from vireon.core.guardrails import GuardrailValidator, GuardrailViolation
            validator = GuardrailValidator()
            validator.validate_experiment_config(self.config)
            print("[VIREON] Neuroethics Guardrails Validated (G1-G8).")
        except GuardrailViolation as e:
            print(f"\n[VIREON] FATAL ERROR: {e}\nSimulation aborted to maintain epistemic integrity.")
            import sys
            sys.exit(1)

        # Register all built-in plugins
        register_builtin_plugins(self.registry)
        
        # Discover and load third-party external plugins via entry points
        self.registry.load_entry_points()

        # 1. Initialize core state
        self.twin = DigitalTwin(
            device_id=self.config.device.device_id,
            sample_rate=self.config.device.sample_rate,
            num_channels=self.config.device.num_channels,
            hardware_mode=self.config.emulation.hardware_loopback,
            seed=self.config.seed
        )
        self.attack_engine = SignalAttackEngine(self.twin, self.event_bus)

        # 1.5 Initialize Threat Intel (Standards Mapping)
        self.threat_intel = self.registry.create("security", "threat_intel")

        # Enable event logging for reproducibility
        self.event_bus.enable_logging(True)

        from vireon.core.coordinator_builder import SimulationBuilder
        builder = SimulationBuilder(self)

        # 2. Configure attacks
        builder.setup_attacks()

        # Configure timed scenarios if scenario steps are defined
        self.scenario = None
        if self.config.attacks.scenario_steps:
            from vireon.core.attack import AttackScenario, AttackStep
            steps = []
            for step_cfg in self.config.attacks.scenario_steps:
                steps.append(AttackStep(
                    time_sec=step_cfg.time_sec,
                    attack_type=step_cfg.attack,
                    duration_sec=step_cfg.duration_sec,
                    target_channels=step_cfg.target_channels,
                    params=step_cfg.params
                ))
            self.scenario = AttackScenario(self.config.name, steps, self.event_bus)

        # 3. Configure data source
        device_wrapper = builder.setup_device()
        dataset_reader = builder.setup_dataset()

        from vireon.core.data_provider import DeviceProviderAdapter, DatasetProviderAdapter
        provider = None
        if device_wrapper:
            provider = DeviceProviderAdapter(device_wrapper)
        elif dataset_reader:
            provider = DatasetProviderAdapter(dataset_reader)

        # 4. Build replay engine
        self.engine = ReplayEngine(
            twin=self.twin,
            attack_engine=self.attack_engine,
            provider=provider,
            seed=self.config.seed,
            loop_dataset=self.config.dataset.loop
        )

        # 5. Clinical simulation
        self.clinical_sim = ClosedLoopSimulator(self.twin)
        if self.config.emulation.dbs_mode or self.config.web.enabled:
            print("[VIREON] Initializing Virtual DBS Controller...")
            from vireon.plugins.clinical.dbs_emulator import ClosedLoopDBSController
            self.dbs_controller = ClosedLoopDBSController(self.twin)

        # 6. Security layer
        if self.config.security.enabled or self.config.web.enabled:
            print("[VIREON] Initializing Neuro Security Layer (IDS/IPS Active)...")
            self.ids = self.registry.create(
                "security", "ids",
                twin=self.twin, event_bus=self.event_bus,
                rms_high_threshold=self.config.security.rms_high_threshold,
                rms_low_threshold=self.config.security.rms_low_threshold,
                beta_power_threshold=self.config.security.beta_power_threshold,
                seed=self.config.seed
            )
            self.ips = self.registry.create(
                "security", "ips",
                twin=self.twin, ids=self.ids, event_bus=self.event_bus,
                max_stimulation_amplitude_ma=self.config.security.max_stimulation_amplitude_ma
            )
            self.link_guard = self.registry.create("security", "ble_guard", twin=self.twin, event_bus=self.event_bus)
            
        # 6.5 NSP Wrapper
        if self.config.security.nsp_enabled or self.config.web.enabled:
            from vireon.plugins.devices.nsp_wrapper import NSPCryptographicWrapper
            self.nsp_wrapper = NSPCryptographicWrapper(simulate_latency_ms=1.5)

        # 6.6 Firmware Emulation
        from vireon.plugins.firmware.cortex_m_stub import CortexMStub
        self.emulator = CortexMStub()
        self.fw_monitor = self.registry.create("security", "fw_monitor", firmware_emulator=self.emulator)

        # 6.7 P300 Leakage Analyzer
        self.p300_analyzer = self.registry.create("security", "p300_analyzer")

        # 6.8 End-to-End Encryption (E2EE)
        self.e2ee_channel = self.registry.create("security", "e2ee_channel")

        # 6.9 Neuro-Biometric Authentication Gate
        # Profile specific to the generated synthetic data (alpha ~ 10Hz)
        self.biometric_gate = self.registry.create("security", "biometric_gate", authorized_profile={"alpha_peak_hz": 10.0})

        # 6.10 Zero-Trust Architecture Policy Engine
        if getattr(self.config.security, 'enable_zta', False):
            self.zta_engine = self.registry.create("security", "zta_engine", thresholds=getattr(self.config.security, 'zta_thresholds', {}))

        # 7. Web server & LSL
        if getattr(self.config.web, 'lsl_only', False):
            builder.setup_lsl_streamer()
        elif self.config.web.enabled:
            builder.setup_web_server()

        # 8. BLE emulation
        if self.config.emulation.ble:
            builder.setup_ble()

        # 8.5 Privacy Engine
        self.privacy_filter = None
        self.privacy_tracker = None
        if self.config.privacy.enabled:
            from vireon.core.privacy import DifferentialPrivacyFilter, PrivacyBudgetTracker
            self.privacy_filter = DifferentialPrivacyFilter(epsilon=self.config.privacy.epsilon)
            self.privacy_tracker = PrivacyBudgetTracker(max_epsilon=10.0)

        from vireon.core.coordinator_callbacks import CoordinatorCallbacks
        self.callbacks = CoordinatorCallbacks(self)
        
        # 9. Register the unified simulation callback
        self.engine.add_callback(self.callbacks.simulation_callback)

        # 10. OpenBCI emulator
        if self.config.emulation.openbci:
            from vireon.plugins.devices.openbci_emulator import OpenBCICytonEmulator
            self.emulator = OpenBCICytonEmulator(self.twin)
            self.emulator.start()
            self.engine.add_callback(self.emulator.send_eeg_data)

        # 11. Initialize Attack Chain (Threat Model) - REMOVED (Dead orchestration)
        self.attack_chain = []
        self.attack_context = {}

        # Publish setup complete event
        self.event_bus.publish(Event(
            topic="experiment.setup_complete",
            data={"config_name": self.config.name, "seed": self.config.seed},
            source="coordinator"
        ))
        self._setup_complete = True

    def run(self):
        """
        Run the simulation loop. Blocks until duration elapsed or KeyboardInterrupt.
        Call setup() first.
        """
        if not self._setup_complete:
            raise RuntimeError("Call setup() before run()")

        # Publish start event
        self.event_bus.publish(Event(
            topic="experiment.started",
            data={"duration": self.config.duration_sec},
            source="coordinator"
        ))

        print(f"[VIREON] Starting simulation (interval={self.config.interval_sec}s, "
              f"duration={self.config.duration_sec}s, "
              f"seed={self.config.seed})...")

        # Execute pre-signal attack stages - REMOVED (Dead orchestration)

        self.engine.start(interval_sec=self.config.interval_sec)
        start_time = time.time()

        try:
            while time.time() - start_time < self.config.duration_sec:
                if self.config.security.enabled and self.link_guard:
                    self.link_guard.check_rf_environment()

                if not self.config.web.enabled:
                    # Terminal telemetry dashboard
                    sys.stdout.write("\033[H\033[J")
                    sys.stdout.write(format_telemetry_table(self.twin))
                    if self.emulator and hasattr(self.emulator, 'slave_name'):
                        sys.stdout.write(f"Virtual Cyton Port : {self.emulator.slave_name}\n")
                    sys.stdout.write(f"\nRemaining Time: {max(0.0, self.config.duration_sec - (time.time() - start_time)):.1f}s\n")
                    sys.stdout.write(f"Sim Clock: {self.engine.sim_clock:.1f}s | Speed: {self.engine.speed:.1f}x\n")
                    if self.engine.is_paused:
                        sys.stdout.write("*** PAUSED ***\n")
                    sys.stdout.flush()
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[VIREON] Simulation interrupted by user.")

        # Publish stop event
        self.event_bus.publish(Event(
            topic="experiment.stopped",
            data={"sim_clock": self.engine.sim_clock},
            source="coordinator"
        ))

    def teardown(self):
        """Graceful shutdown of all components."""
        print("\n[VIREON] Stopping replay engine...")
        if self.engine:
            self.engine.stop()
        if self.emulator and hasattr(self.emulator, 'stop'):
            self.emulator.stop()
        if self.bridge:
            self.bridge.stop()
        if self.web_server:
            print("[VIREON] Stopping Web UI server...")
            self.web_server.shutdown()
            self.web_server.server_close()
        if self.ws_server:
            print("[VIREON] Stopping WebSocket server...")
            self.ws_server.stop()

        # Report compilation
        if self.config.output.no_report or self.config.web.enabled:
            print("\n[VIREON] Report compilation bypassed.")
        else:
            self._compile_reports()

    # --- WebSocket broadcast callback moved to coordinator_callbacks.py ---

    # --- Builder setup helpers were moved to coordinator_builder.py ---

    # --- Trust context and Simulation callbacks moved to coordinator_callbacks.py ---
    def simulate_firmware_update(self, payload: bytes) -> bool:
        """Simulates an OTA firmware update with anti-rollback support and ZTA checks."""
        if self.emulator:
            print(f"[Coordinator] Simulating OTA Firmware Update ({len(payload)} bytes)...")
            
            # ZTA Pre-Check
            if self.zta_engine:
                from vireon.core.zta import AuthorizationDecision
                ctx = self._build_trust_context()
                decision = self.zta_engine.evaluate_request("ota_update", ctx)
                if decision == AuthorizationDecision.DENY:
                    print("[Coordinator] ZTA Policy Engine blocked OTA Firmware Update (Trust score too low).")
                    self.twin.set_clinical_alert(True, "ZTA Blocked OTA Update Attempt")
                    return False
            
            # Check if require_signed_ota is configured (defaults to True for Phase 3)
            require_signed_ota = getattr(self.config.security, 'require_signed_ota', True)
            
            if require_signed_ota:
                success = self.emulator.process_ota_update(payload)
            else:
                success = self.emulator.write_memory(self.emulator.FLASH_BASE, payload)
                
            if not success:
                print(f"[Coordinator] FIRMWARE FAULT: {self.emulator.crash_reason}")
                self.twin.set_clinical_alert(True, f"Firmware Fault: {self.emulator.crash_reason}")
            return success
        return False

    def _compile_reports(self):
        """Generate audit reports after simulation."""
        print("[VIREON] Compiling audit reports...")

        if self.config.emulation.dbs_mode and self.dbs_controller:
            summary = self.dbs_controller.get_clinical_summary()
        else:
            summary = self.clinical_sim.get_clinical_summary()

        if self.config.security.enabled and self.ips:
            summary["security_active"] = True
            summary["blocked_attacks_count"] = self.ips.blocked_attacks_count
            summary["clamping_active"] = self.ips.clamping_active
            if self.link_guard:
                summary["blocked_mtu_abuses"] = self.link_guard.blocked_mtu_abuses
        else:
            summary["security_active"] = False
            summary["blocked_attacks_count"] = 0
            summary["clamping_active"] = False
            summary["blocked_mtu_abuses"] = 0
            
        summary["nsp_active"] = self.twin.nsp_mode
        summary["p300_leakage_events"] = self.total_p300_leakage_events

        from vireon.plugins.reports.generator import ReportGenerator
                
        generator = ReportGenerator(self.twin)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        prefix_with_time = f"{self.config.output.report_prefix}_{timestamp}"
        
        generator.compile_report(summary, prefix_with_time, anonymize_exports=self.config.privacy.anonymize_exports)

        print("\n" + "=" * 60)
        print(" SIMULATION COMPLETE")
        print("-" * 60)
        print(f" Clinical Status: {summary['current_status']}")
        print(f" Alert Active:    {summary['alert_active']}")
        print(f" Hazard State:    {summary.get('hazard_state', 'NOMINAL')}")
        print(f" ISO Severity:    {summary.get('iso_severity', 'NEGLIGIBLE')}")
        print(f" Mean Confidence: {summary['average_confidence']:.2f}")
        if self.config.security.enabled:
            print(" Security Shield: ACTIVE (IDS/IPS Enabled)")
            print(f" Blocked Attacks: {summary.get('blocked_attacks_count', 0)}")
        print(f" Seed:            {self.config.seed}")
        print("=== VIREON REPORTS ===")
        print(f"  - HTML Log:     {self.config.output.report_prefix}_report.html")
        print(f"  - PDF Report:   {self.config.output.report_prefix}_report.pdf")
        print(f"  - Markdown Log: {self.config.output.report_prefix}_report.md")
        print(f"  - JSON DB:      {self.config.output.report_prefix}_telemetry.json")
        print("=" * 60)

    def _build_trust_context(self):
        from vireon.core.zta import TrustContext
        
        return TrustContext(
            biometric_confidence=getattr(self.twin, 'decoder_confidence', 0.0),
            firmware_healthy=getattr(self.twin, 'clinical_status', '') != "Crashed",
            e2ee_established=getattr(self.twin, 'secure_mode', False),
            clinical_mode=getattr(self.twin, 'clinical_status', '') == "Nominal"
        )
