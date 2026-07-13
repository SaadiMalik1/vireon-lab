"""
NeuroShield Coordinator — Central orchestrator for the simulation pipeline.

Replaces the monolithic main() function with a properly structured class
that can be used both programmatically and from the CLI.
"""

import os
import sys
import time
import numpy as np
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

from neuroshield.core.twin import DigitalTwin
from neuroshield.core.engine import ReplayEngine
from neuroshield.core.attack import SignalAttackEngine, NoiseInjectionAttack, SignalDriftAttack, ImpedanceSpikeAttack, SignalSuppressionAttack
from neuroshield.core.event_bus import EventBus, Event
from neuroshield.core.config import ExperimentConfig
from neuroshield.core.plugin_registry import PluginRegistry, register_builtin_plugins
from neuroshield.core.utils import format_telemetry_table
from neuroshield.plugins.clinical.closed_loop import ClosedLoopSimulator


class Coordinator:
    """
    Orchestrates a NeuroShield simulation experiment.

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

        # Optional components (initialized during setup based on config)
        self.clinical_sim: Optional[ClosedLoopSimulator] = None
        self.dbs_controller = None
        self.ids = None
        self.ips = None
        self.link_guard = None
        self.emulator = None
        self.ble_server = None
        self.ble_link = None
        self.ble_client = None
        self.bridge = None
        self.web_server = None
        self.ws_server = None
        self.lsl_streamer = None
        self.threat_intel = None
        self.nsp_wrapper = None

        # Shared mutable simulation context for web UI control
        # (backward compat with existing web_server.py)
        self._simulation_context: Dict[str, Any] = {
            "dbs_mode": config.emulation.dbs_mode,
            "secure_mode": config.security.enabled,
            "nsp_mode": config.security.nsp_enabled,
            "dbs_attack": config.emulation.dbs_attack,
            "active_attack": "none",
            "noise_intensity": config.attacks.noise_level_uv,
            "attenuation_factor": config.attacks.attenuation_factor,
            "impedance_kohm": config.attacks.spike_impedance_kohm,
        }

        self._setup_complete = False

    @property
    def simulation_context(self) -> Dict[str, Any]:
        return self._simulation_context

    def setup(self):
        """Initialize all components based on config. Call once before run()."""
        print("[NeuroShield] Initializing Virtual Laboratory...")
        
        # 0. Enforce Neuroethics Guardrails
        try:
            from neuroshield.core.guardrails import GuardrailValidator, GuardrailViolation
            validator = GuardrailValidator()
            validator.validate_experiment_config(self.config)
            print("[NeuroShield] Neuroethics Guardrails Validated (G1-G8).")
        except GuardrailViolation as e:
            print(f"\n[NeuroShield] FATAL ERROR: {e}\nSimulation aborted to maintain epistemic integrity.")
            import sys
            sys.exit(1)

        # Register all built-in plugins
        register_builtin_plugins(self.registry)
        
        # Discover and load third-party external plugins via entry points
        self.registry.load_entry_points()

        # 1. Initialize core state
        self.twin = DigitalTwin(
            device_id=f"virtual_{self.config.device.type}_board",
            sample_rate=self.config.device.sample_rate,
            num_channels=self.config.device.num_channels
        )
        self.attack_engine = SignalAttackEngine(self.twin, self.event_bus)

        # 1.5 Initialize Threat Intel (TARA Mapping)
        try:
            from neuroshield.core.threat_intel import ThreatIntelligence
            # Default path to the neurosecurity submodule/directory
            registry_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "neurosecurity", "datalake", "qtara-registrar.json")
            self.threat_intel = ThreatIntelligence(registry_path)
        except Exception as e:
            logger.error(f"Could not initialize ThreatIntelligence", exc_info=True)
            self.threat_intel = None

        # Enable event logging for reproducibility
        self.event_bus.enable_logging(True)

        # 2. Configure attacks
        self._setup_attacks()

        # Configure timed scenarios if scenario steps are defined
        self.scenario = None
        if self.config.attacks.scenario_steps:
            from neuroshield.core.attack import AttackScenario, AttackStep
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
        device_wrapper = self._setup_device()
        dataset_reader = self._setup_dataset()

        # 4. Build replay engine
        self.engine = ReplayEngine(
            twin=self.twin,
            attack_engine=self.attack_engine,
            device_wrapper=device_wrapper,
            dataset_reader=dataset_reader,
            seed=self.config.seed,
            loop_dataset=self.config.dataset.loop
        )

        # 5. Clinical simulation
        self.clinical_sim = ClosedLoopSimulator(self.twin)
        if self.config.emulation.dbs_mode or self.config.web.enabled:
            print("[NeuroShield] Initializing Virtual DBS Controller...")
            from neuroshield.plugins.clinical.dbs_emulator import ClosedLoopDBSController
            self.dbs_controller = ClosedLoopDBSController(self.twin)

        # 6. Security layer
        if self.config.security.enabled or self.config.web.enabled:
            print("[NeuroShield] Initializing Neuro Security Layer (IDS/IPS Active)...")
            from neuroshield.core.security import NeuroIDS, NeuroIPS, BLELinkGuard
            self.ids = NeuroIDS(
                self.twin, self.event_bus,
                rms_high_threshold=self.config.security.rms_high_threshold,
                rms_low_threshold=self.config.security.rms_low_threshold,
                beta_power_threshold=self.config.security.beta_power_threshold
            )
            self.ips = NeuroIPS(
                self.twin, self.ids, self.event_bus,
                max_stimulation_amplitude_ma=self.config.security.max_stimulation_amplitude_ma
            )
            self.link_guard = BLELinkGuard(self.twin, self.event_bus)
            
        # 6.5 NSP Wrapper
        if self.config.security.nsp_enabled or self.config.web.enabled:
            from neuroshield.plugins.devices.nsp_wrapper import NSPCryptographicWrapper
            self.nsp_wrapper = NSPCryptographicWrapper(simulate_latency_ms=1.5)

        # 7. Web server & LSL
        if getattr(self.config.web, 'lsl_only', False):
            self._setup_lsl_streamer()
        elif self.config.web.enabled:
            self._setup_web_server()

        # 8. BLE emulation
        if self.config.emulation.ble:
            self._setup_ble()

        # 9. Register the unified simulation callback
        self.engine.add_callback(self._simulation_callback)

        # 10. OpenBCI emulator
        if self.config.emulation.openbci:
            from neuroshield.plugins.devices.openbci_emulator import OpenBCICytonEmulator
            self.emulator = OpenBCICytonEmulator(self.twin)
            self.emulator.start()
            self.engine.add_callback(self.emulator.send_eeg_data)

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

        print(f"[NeuroShield] Starting simulation (interval={self.config.interval_sec}s, "
              f"duration={self.config.duration_sec}s, "
              f"seed={self.config.seed})...")

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
                    if self.emulator:
                        sys.stdout.write(f"Virtual Cyton Port : {self.emulator.slave_name}\n")
                    sys.stdout.write(f"\nRemaining Time: {max(0.0, self.config.duration_sec - (time.time() - start_time)):.1f}s\n")
                    sys.stdout.write(f"Sim Clock: {self.engine.sim_clock:.1f}s | Speed: {self.engine.speed:.1f}x\n")
                    if self.engine.is_paused:
                        sys.stdout.write("*** PAUSED ***\n")
                    sys.stdout.flush()
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[NeuroShield] Simulation interrupted by user.")

        # Publish stop event
        self.event_bus.publish(Event(
            topic="experiment.stopped",
            data={"sim_clock": self.engine.sim_clock},
            source="coordinator"
        ))

    def teardown(self):
        """Graceful shutdown of all components."""
        print("\n[NeuroShield] Stopping replay engine...")
        if self.engine:
            self.engine.stop()
        if self.emulator:
            self.emulator.stop()
        if self.bridge:
            self.bridge.stop()
        if self.web_server:
            print("[NeuroShield] Stopping Web UI server...")
            self.web_server.shutdown()
            self.web_server.server_close()
        if self.ws_server:
            print("[NeuroShield] Stopping WebSocket server...")
            self.ws_server.stop()

        # Report compilation
        if self.config.output.no_report or self.config.web.enabled:
            print("\n[NeuroShield] Report compilation bypassed.")
        else:
            self._compile_reports()

    def _ws_broadcast_callback(self, data, channels, sample_rate):
        """Callback to serialize and broadcast simulation state over WebSockets."""
        if self.ws_server is not None:
            import json
            state = self.twin.get_state()
            # Send Channel 1 signal chunk as JSON-serializable list (Ch 0 is often package count)
            # Replace NaNs with 0.0 because standard JSON (and JS JSON.parse) cannot handle NaN
            signal_list = data[1, :].tolist()
            state["signal_chunk"] = [0.0 if np.isnan(x) else x for x in signal_list]
            
            active_attack = self._simulation_context.get("active_attack", "none")
            state["active_attack"] = active_attack
            if self.threat_intel and active_attack != "none":
                tara_intel = self.threat_intel.resolve_attack(active_attack)
                if tara_intel:
                    state["threat_intel"] = tara_intel
            
            if hasattr(self, 'ids') and self.ids:
                state["security_logs"] = list(self.ids.detections)
                
            if hasattr(self, 'ips') and self.ips:
                state["blocked_attacks_count"] = self.ips.blocked_attacks_count
                state["clamping_active"] = self.ips.clamping_active
                state["blocked_mtu_abuses"] = self.ips.blocked_mtu_abuses
                
            if self._simulation_context.get("nsp_mode", False) and self.nsp_wrapper:
                state = self.nsp_wrapper.encrypt_payload(state)
                
            self.ws_server.broadcast_sync(json.dumps(state))

    # --- Private setup helpers ---

    def _setup_attacks(self):
        """Configure signal modifiers from config."""
        target_channels = self.config.attacks.target_channels

        for attack_name in self.config.attacks.active:
            if attack_name == "noise":
                print(f"[NeuroShield] Injecting Noise Attack (SD={self.config.attacks.noise_level_uv} uV)")
                self.attack_engine.add_modifier(
                    NoiseInjectionAttack(target_channels, self.config.attacks.noise_level_uv)
                )
            elif attack_name == "drift":
                print(f"[NeuroShield] Injecting Signal Drift Attack")
                self.attack_engine.add_modifier(
                    SignalDriftAttack(target_channels, self.config.attacks.drift_rate_uv_per_sec)
                )
            elif attack_name == "impedance":
                print(f"[NeuroShield] Injecting Impedance Spike Attack")
                self.attack_engine.add_modifier(
                    ImpedanceSpikeAttack(target_channels, self.config.attacks.spike_impedance_kohm)
                )
            elif attack_name == "suppression":
                print(f"[NeuroShield] Injecting Signal Suppression Attack")
                self.attack_engine.add_modifier(
                    SignalSuppressionAttack(target_channels, self.config.attacks.attenuation_factor)
                )
            elif attack_name == "stimulation_leak":
                print("[NeuroShield] Injecting Stimulation Leak Attack")
                if self.config.security.enabled:
                    from neuroshield.core.security import NeuroIDS, NeuroIPS
                    temp_ids = NeuroIDS(self.twin)
                    temp_ips = NeuroIPS(self.twin, temp_ids)
                    amp, freq = temp_ips.sanitize_stimulation_write(10.0, 130.0)
                    self.twin.update_therapy(True)
                    self.twin.update_stimulation_params(amp, freq)
                else:
                    from neuroshield.plugins.clinical.closed_loop import UncontrolledStimulationAttack
                    leak = UncontrolledStimulationAttack(self.twin)
                    leak.apply()
            else:
                print(f"[NeuroShield] Warning: Unknown attack type: {attack_name}")

        self.event_bus.publish(Event(
            topic="attack.configured",
            data={"attacks": self.config.attacks.active},
            source="coordinator"
        ))

    def _setup_device(self):
        """Load device wrapper from config."""
        device_wrapper = None
        try:
            if self.registry.has("devices", self.config.device.type):
                device_wrapper = self.registry.create(
                    "devices", 
                    self.config.device.type,
                    serial_port=self.config.device.serial_port
                )
            else:
                print(f"[NeuroShield] Warning: Unknown device type '{self.config.device.type}'")
        except Exception as e:
            logger.error(f"Error loading device module", exc_info=True)
            sys.exit(1)
        return device_wrapper

    def _setup_dataset(self):
        """Load dataset reader from config."""
        dataset_reader = None

        if self.config.emulation.hardware_loopback:
            print("[NeuroShield] Configuring Hardware-in-the-loop (HIL) Socket Bridge...")
            from neuroshield.plugins.devices.hardware_bridge import HardwareBridge
            self.bridge = HardwareBridge(host="127.0.0.1", port=9090)
            self.bridge.start()
            dataset_reader = self.bridge
        elif self.config.dataset.path:
            path = self.config.dataset.path
            ext = os.path.splitext(path)[1].lower()
            if ext in [".edf", ".bdf"]:
                from neuroshield.plugins.datasets.edf_reader import EDFReader
                dataset_reader = EDFReader(path)
            elif ext == ".csv":
                from neuroshield.plugins.datasets.csv_reader import CSVReader
                dataset_reader = CSVReader(path)
            else:
                print(f"[NeuroShield] Unsupported dataset extension: {ext}. Using synthetic stream.")

        return dataset_reader

    def _setup_lsl_streamer(self):
        """Initialize LSL Streamer instead of Web UI."""
        print(f"[NeuroShield] Bypassing Web UI. Initializing LSL Streamer...")
        try:
            from neuroshield.core.lsl_streamer import LSLStreamer
            self.lsl_streamer = LSLStreamer(num_channels=self.twin.num_channels, srate=self.twin.sample_rate)
            self.config.duration_sec = 100000.0  # Run indefinitely in LSL mode
        except Exception as e:
            logger.error(f"Failed to start LSL Streamer", exc_info=True)

    def _setup_web_server(self):
        """Start the Web UI dashboard."""
        import webbrowser
        import secrets
        from neuroshield.plugins.reports.web_server import start_web_server, simulation_context
        
        # Generate a secure session token for WebSocket authentication
        self.ws_token = secrets.token_urlsafe(16)

        # Pre-seed the context with current settings
        simulation_context["secure_mode"] = self.config.security.enabled
        simulation_context["hardware_mode"] = self.config.emulation.hardware_loopback
        
        self.web_server = start_web_server(
            twin=self.twin,
            attack_engine=self.attack_engine,
            port=self.config.web.port,
            ips=self.ips,
            link_guard=self.link_guard,
            ws_token=self.ws_token
        )
        
        # Also start the fast telemetry websocket server
        from neuroshield.plugins.reports.ws_server import NeuroWebSocketServer
        self.ws_server = NeuroWebSocketServer(port=self.config.web.port + 1, token=self.ws_token)
        self.ws_server.start()

        # Add WebSocket broadcast callback to the engine
        self.engine.add_callback(self._ws_broadcast_callback)

        if self.config.web.open_browser:
            webbrowser.open(f"http://127.0.0.1:{self.config.web.port}")

    def _setup_ble(self):
        """Initialize BLE emulation stack."""
        from neuroshield.plugins.ble.emulator import VirtualBLEServer, VirtualBLELink, VirtualBLEClient
        from neuroshield.plugins.ble.attacks import PairingFailureAttack, MTUAbuseAttack

        print("[NeuroShield] Initializing Virtual BLE Stack...")
        self.ble_server = VirtualBLEServer()
        self.ble_link = VirtualBLELink(self.ble_server)
        self.ble_client = VirtualBLEClient(self.ble_link)

        self.ble_client.connect()
        self.ble_client.pair("123456")

        requested_mtu = 247
        if self.config.emulation.ble_attack == "mtu_abuse":
            requested_mtu = 5
        if self.config.security.enabled and self.link_guard:
            requested_mtu = self.link_guard.verify_mtu(requested_mtu)
        self.ble_client.negotiate_mtu(requested_mtu)
        self.ble_client.enable_notifications("FE8D", "2D30", True)

        if self.config.emulation.ble_attack == "pairing_fail":
            PairingFailureAttack(self.twin).apply(self.ble_client, self.ble_link)
        elif self.config.emulation.ble_attack == "mtu_abuse" and not self.config.security.enabled:
            MTUAbuseAttack(self.twin, abnormal_mtu=5).apply(self.ble_client, self.ble_link)

    def _simulation_callback(self, raw_data, eeg_channels, sample_rate):
        """Unified simulation callback pipeline — replaces the inline closure in old main.py."""
        import random

        num_samples = raw_data.shape[1]

        # 0. Update timed attack scenario if loaded
        if self.scenario and self.engine:
            self.scenario.update(self.engine.sim_clock, self.attack_engine, self.registry)

        # Resolve active flags dynamically (supports web UI live toggling)
        dbs_active = self._simulation_context["dbs_mode"]
        secure_active = self._simulation_context["secure_mode"]

        # 1. Acquire signal source
        if dbs_active and self.dbs_controller:
            data_to_process = self.dbs_controller.lfp_generator.read_chunk(
                num_samples, self.dbs_controller.stimulation_mode
            )
            raw_data[:data_to_process.shape[0], :] = data_to_process[:, :]
        else:
            data_to_process = raw_data.copy()

        # Simulate physical ADC input amplifier saturation limits
        data_to_process = self.twin.simulate_adc_saturation(data_to_process)

        # IDS/IPS signal filtering
        if secure_active and self.ids and self.ips:
            anomalies = self.ids.analyze_signal(data_to_process)
            data_to_process = self.ips.mitigate_signal_anomalies(data_to_process, anomalies)

            if anomalies:
                self.event_bus.publish(Event(
                    topic="ids.anomaly_detected",
                    data={"anomalies": anomalies, "sim_clock": self.engine.sim_clock},
                    source="ids"
                ))

        # 2. BLE transmission layer
        if self.config.emulation.ble and self.ble_link and self.ble_client:
            if not self.ble_link.connected:
                self.twin.set_connection(False)
                return

            payload = data_to_process.tobytes()

            from neuroshield.plugins.ble.attacks import GATTCorruptionAttack, MalformedNotificationAttack
            if self.config.emulation.ble_attack == "gatt_corrupt":
                payload = GATTCorruptionAttack(corruption_probability=1.0).apply(payload)
            elif self.config.emulation.ble_attack == "malformed_notify":
                attack = MalformedNotificationAttack(packet_size=len(payload))
                payload = attack.apply()

            self.ble_client.receive_notification(payload)

            try:
                reconstructed_bytes = b"".join(self.ble_client.received_packets)
                self.ble_client.received_packets.clear()

                if self.ble_link.mtu < 23:
                    if random.random() < 0.8:
                        raise ValueError("Packet loss under restricted MTU")

                data_to_process = np.frombuffer(
                    reconstructed_bytes[:raw_data.nbytes], dtype=raw_data.dtype
                ).copy().reshape(raw_data.shape)
            except Exception as e:
                logger.error("BLE packet reconstruction failed", exc_info=True)
                data_to_process = np.random.normal(0, 500.0, raw_data.shape)

            if secure_active and self.ids and self.ips:
                anomalies = self.ids.analyze_signal(data_to_process)
                data_to_process = self.ips.mitigate_signal_anomalies(data_to_process, anomalies)

        # 3. Clinical closed-loop evaluation
        if dbs_active and self.dbs_controller:
            dbs_attack_type = self._simulation_context.get("dbs_attack", "")
            self.dbs_controller.process_lfp(
                data_to_process, eeg_channels, sample_rate,
                attack_active=(dbs_attack_type == "phase_shift")
            )
            if secure_active and self.ids and self.ips and self.dbs_controller.history_beta_power:
                curr_pow = self.dbs_controller.history_beta_power[-1]
                stim_active = self.twin.stimulation_enabled
                stim_amp = self.twin.stimulation_amplitude_ma
                clinical_anomalies = self.ids.analyze_clinical(curr_pow, stim_active, stim_amp)
                self.ips.mitigate_pathological_sync(clinical_anomalies)
        else:
            self.clinical_sim.process_signal(data_to_process, eeg_channels, sample_rate)

        # 4. Push final data to LSL if active
        if self.lsl_streamer:
            self.lsl_streamer.push_eeg_chunk(data_to_process)
            
            active_attack = self._simulation_context.get("active_attack", "none")
            telemetry = {
                "sim_clock": self.engine.sim_clock,
                "niss_score": self.twin.niss_score,
                "hazard_state": self.twin.hazard_state,
                "iso_severity": self.twin.iso_severity,
                "temperature_celsius": self.twin.temperature_celsius,
                "active_attack": active_attack
            }
            
            # Map Active Attack to TARA Intel
            if self.threat_intel and active_attack != "none":
                tara_intel = self.threat_intel.resolve_attack(active_attack)
                if tara_intel:
                    telemetry["threat_intel"] = tara_intel
            
            if self.config.security.enabled and self.ids:
                telemetry["mean_confidence"] = self.ids.history_confidence[-1] if self.ids.history_confidence else 1.0
                
            if self._simulation_context.get("nsp_mode", False) and self.nsp_wrapper:
                telemetry = self.nsp_wrapper.encrypt_payload(telemetry)
                
            self.lsl_streamer.push_telemetry(telemetry)

    def _compile_reports(self):
        """Generate audit reports after simulation."""
        print("[NeuroShield] Compiling audit reports...")

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
            
        summary["nsp_active"] = self._simulation_context.get("nsp_mode", False)

        from neuroshield.plugins.reports.generator import ReportGenerator
        import time
        
        generator = ReportGenerator(self.twin)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        prefix_with_time = f"{self.config.output.report_prefix}_{timestamp}"
        
        generator.compile_report(summary, prefix_with_time)

        print("\n" + "=" * 60)
        print(" SIMULATION COMPLETE")
        print("-" * 60)
        print(f" Clinical Status: {summary['current_status']}")
        print(f" Alert Active:    {summary['alert_active']}")
        print(f" Hazard State:    {summary.get('hazard_state', 'NOMINAL')}")
        print(f" ISO Severity:    {summary.get('iso_severity', 'NEGLIGIBLE')}")
        print(f" Mean Confidence: {summary['average_confidence']:.2f}")
        if self.config.security.enabled:
            print(f" Security Shield: ACTIVE (IDS/IPS Enabled)")
            print(f" Blocked Attacks: {summary.get('blocked_attacks_count', 0)}")
        print(f" Seed:            {self.config.seed}")
        print("=== NEUROSHIELD REPORTS ===")
        print(f"  - HTML Log:     {self.config.output.report_prefix}_report.html")
        print(f"  - PDF Report:   {self.config.output.report_prefix}_report.pdf")
        print(f"  - Markdown Log: {self.config.output.report_prefix}_report.md")
        print(f"  - JSON DB:      {self.config.output.report_prefix}_telemetry.json")
        print("=" * 60)
