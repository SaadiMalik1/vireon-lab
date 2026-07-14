"""
VIREON Coordinator — Central orchestrator for the simulation pipeline.

Replaces the monolithic main() function with a properly structured class
that can be used both programmatically and from the CLI.
"""

import time
import sys
import os
import threading
import numpy as np
import logging
from typing import Optional, Dict, Any

from vireon.core.twin import DigitalTwin
from vireon.core.engine import ReplayEngine
from vireon.core.attack import SignalAttackEngine, NoiseInjectionAttack, SignalDriftAttack, ImpedanceSpikeAttack, SignalSuppressionAttack
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
        self.dbs_controller = None
        self.ids = None
        self.ips = None
        self.link_guard = None
        self.emulator = None
        self.fw_monitor = None
        self.ble_server = None
        self.p300_analyzer = None
        self.total_p300_leakage_events = 0
        self.e2ee_channel = None
        self.biometric_gate = None
        self.ble_link = None
        self.ble_client = None
        self.bridge = None
        self.web_server = None
        self.ws_server = None
        self.lsl_streamer = None
        self.threat_intel = None
        self.nsp_wrapper = None
        self.zta_engine = None

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
            device_id=f"virtual_{self.config.device.type}_board",
            sample_rate=self.config.device.sample_rate,
            num_channels=self.config.device.num_channels
        )
        self.attack_engine = SignalAttackEngine(self.twin, self.event_bus)

        # 1.5 Initialize Threat Intel (Standards Mapping)
        try:
            from vireon.core.threat_intel import ThreatIntelligence
            self.threat_intel = ThreatIntelligence()

        except Exception:
            logger.error("Could not initialize ThreatIntelligence", exc_info=True)
            self.threat_intel = None

        # Enable event logging for reproducibility
        self.event_bus.enable_logging(True)

        # 2. Configure attacks
        self._setup_attacks()

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
            print("[VIREON] Initializing Virtual DBS Controller...")
            from vireon.plugins.clinical.dbs_emulator import ClosedLoopDBSController
            self.dbs_controller = ClosedLoopDBSController(self.twin)

        # 6. Security layer
        if self.config.security.enabled or self.config.web.enabled:
            print("[VIREON] Initializing Neuro Security Layer (IDS/IPS Active)...")
            from vireon.core.security import NeuroSignalAssuranceEngine, NeuroIPS, BLELinkGuard
            self.ids = NeuroSignalAssuranceEngine(
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
            from vireon.plugins.devices.nsp_wrapper import NSPCryptographicWrapper
            self.nsp_wrapper = NSPCryptographicWrapper(simulate_latency_ms=1.5)

        # 6.6 Firmware Emulation
        from vireon.plugins.firmware.cortex_m_stub import CortexMStub, FirmwareSecurityMonitor
        self.emulator = CortexMStub()
        self.fw_monitor = FirmwareSecurityMonitor(self.emulator)

        # 6.7 P300 Leakage Analyzer
        from vireon.core.privacy_leakage import P300Analyzer
        self.p300_analyzer = P300Analyzer()

        # 6.8 End-to-End Encryption (E2EE)
        from vireon.core.e2ee import E2EEChannel
        self.e2ee_channel = E2EEChannel()

        # 6.9 Neuro-Biometric Authentication Gate
        from vireon.core.authentication import BiometricGate
        # Profile specific to the generated synthetic data (alpha ~ 10Hz)
        self.biometric_gate = BiometricGate(authorized_profile={"alpha_peak_hz": 10.0})

        # 6.10 Zero-Trust Architecture Policy Engine
        if getattr(self.config.security, 'enable_zta', False):
            from vireon.core.zta import ZTAPolicyEngine
            self.zta_engine = ZTAPolicyEngine(thresholds=getattr(self.config.security, 'zta_thresholds', {}))

        # 7. Web server & LSL
        if getattr(self.config.web, 'lsl_only', False):
            self._setup_lsl_streamer()
        elif self.config.web.enabled:
            self._setup_web_server()

        # 8. BLE emulation
        if self.config.emulation.ble:
            self._setup_ble()

        # 8.5 Privacy Engine
        self.privacy_filter = None
        self.privacy_tracker = None
        if self.config.privacy.enabled:
            from vireon.core.privacy import DifferentialPrivacyFilter, PrivacyBudgetTracker
            self.privacy_filter = DifferentialPrivacyFilter(epsilon=self.config.privacy.epsilon)
            self.privacy_tracker = PrivacyBudgetTracker(max_epsilon=10.0)

        # 9. Register the unified simulation callback
        self.engine.add_callback(self._simulation_callback)

        # 10. OpenBCI emulator
        if self.config.emulation.openbci:
            from vireon.plugins.devices.openbci_emulator import OpenBCICytonEmulator
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

        print(f"[VIREON] Starting simulation (interval={self.config.interval_sec}s, "
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

    def _ws_broadcast_callback(self, data, channels, sample_rate):
        """Callback to serialize and broadcast simulation state over WebSockets."""
        if self.ws_server is not None:
            import json
            state = self.twin.get_state()
            # Send Channel 1 signal chunk as JSON-serializable list (Ch 0 is often package count)
            # Replace NaNs with 0.0 because standard JSON (and JS JSON.parse) cannot handle NaN
            signal_chunk = data[1, :]
            
            # Apply Differential Privacy if enabled
            if self.privacy_filter is not None:
                # We need to reshape slightly or just pass the 1D array
                signal_chunk = self.privacy_filter.filter_signal(signal_chunk.copy())
                if self.privacy_tracker:
                    self.privacy_tracker.consume(0.001)  # Nominal budget consumption per chunk
                    
            signal_list = signal_chunk.tolist()
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
                print(f"[VIREON] Injecting Noise Attack (SD={self.config.attacks.noise_level_uv} uV)")
                self.attack_engine.add_modifier(
                    NoiseInjectionAttack(target_channels, self.config.attacks.noise_level_uv)
                )
            elif attack_name == "drift":
                print("[VIREON] Injecting Signal Drift Attack")
                self.attack_engine.add_modifier(
                    SignalDriftAttack(target_channels, self.config.attacks.drift_rate_uv_per_sec)
                )
            elif attack_name == "impedance":
                print("[VIREON] Injecting Impedance Spike Attack")
                self.attack_engine.add_modifier(
                    ImpedanceSpikeAttack(target_channels, self.config.attacks.spike_impedance_kohm)
                )
            elif attack_name == "suppression":
                print("[VIREON] Injecting Signal Suppression Attack")
                self.attack_engine.add_modifier(
                    SignalSuppressionAttack(target_channels, self.config.attacks.attenuation_factor)
                )
            elif attack_name == "stimulation_leak":
                print("[VIREON] Injecting Stimulation Leak Attack")
                if self.config.security.enabled:
                    from vireon.core.security import NeuroSignalAssuranceEngine, NeuroIPS
                    temp_ids = NeuroSignalAssuranceEngine(self.twin)
                    temp_ips = NeuroIPS(self.twin, temp_ids)
                    amp, freq = temp_ips.sanitize_stimulation_write(10.0, 130.0)
                    self.twin.update_therapy(True)
                    self.twin.update_stimulation_params(amp, freq)
                else:
                    from vireon.plugins.clinical.closed_loop import UncontrolledStimulationAttack
                    leak = UncontrolledStimulationAttack(self.twin)
                    leak.apply()
            else:
                print(f"[VIREON] Warning: Unknown attack type: {attack_name}")

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
                print(f"[VIREON] Warning: Unknown device type '{self.config.device.type}'")
        except Exception:
            logger.error("Error loading device module", exc_info=True)
            sys.exit(1)
        return device_wrapper

    def _setup_dataset(self):
        """Load dataset reader from config."""
        dataset_reader = None

        if self.config.emulation.hardware_loopback:
            print("[VIREON] Configuring Hardware-in-the-loop (HIL) Socket Bridge...")
            from vireon.plugins.devices.hardware_bridge import HardwareBridge
            self.bridge = HardwareBridge(host="127.0.0.1", port=9090)
            self.bridge.start()
            dataset_reader = self.bridge
        elif self.config.dataset.path:
            path = self.config.dataset.path
            ext = os.path.splitext(path)[1].lower()
            if ext in [".edf", ".bdf"]:
                from vireon.plugins.datasets.edf_reader import EDFReader
                dataset_reader = EDFReader(path)
            elif ext == ".csv":
                from vireon.plugins.datasets.csv_reader import CSVReader
                dataset_reader = CSVReader(path)
            else:
                print(f"[VIREON] Unsupported dataset extension: {ext}. Using synthetic stream.")

        return dataset_reader

    def _setup_lsl_streamer(self):
        """Initialize LSL Streamer instead of Web UI."""
        print("[VIREON] Bypassing Web UI. Initializing LSL Streamer...")
        try:
            from vireon.core.lsl_streamer import LSLStreamer
            self.lsl_streamer = LSLStreamer(num_channels=self.twin.num_channels, srate=self.twin.sample_rate)
            self.config.duration_sec = 100000.0  # Run indefinitely in LSL mode
        except Exception:
            logger.error("Failed to start LSL Streamer", exc_info=True)

    def _setup_web_server(self):
        """Start the Web UI dashboard."""
        import webbrowser
        import secrets
        from vireon.plugins.reports.web_server import start_web_server, simulation_context
        
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
        from vireon.plugins.reports.ws_server import NeuroWebSocketServer
        self.ws_server = NeuroWebSocketServer(port=self.config.web.port + 1, token=self.ws_token)
        self.ws_server.start()

        # Add WebSocket broadcast callback to the engine
        self.engine.add_callback(self._ws_broadcast_callback)

        if self.config.web.open_browser:
            webbrowser.open(f"http://127.0.0.1:{self.config.web.port}")

    def _setup_ble(self):
        """Initialize BLE emulation stack."""
        from vireon.plugins.ble.emulator import VirtualBLEServer, VirtualBLELink, VirtualBLEClient
        from vireon.plugins.ble.attacks import PairingFailureAttack, MTUAbuseAttack

        print("[VIREON] Initializing Virtual BLE Stack...")
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

    def _build_trust_context(self):
        from vireon.core.zta import TrustContext
        
        # Determine biometric confidence
        bio_conf = 1.0
        if self.biometric_gate and not self.biometric_gate.is_unlocked:
            bio_conf = 0.0
        elif self.ids and self.ids.history_confidence:
            bio_conf = self.ids.history_confidence[-1]

        return TrustContext(
            biometric_confidence=bio_conf,
            firmware_healthy=not getattr(self.emulator, 'crashed', False) if self.emulator else True,
            e2ee_established=self._simulation_context.get("e2ee_mode", False),
            clinical_mode=True # Defaulting to True for simulation purposes
        )

    def _simulation_callback(self, raw_data, eeg_channels, sample_rate):
        """Unified callback executed every block by the ReplayEngine."""
        
        # 0. ZTA Telemetry Check
        if self.zta_engine:
            from vireon.core.zta import AuthorizationDecision
            ctx = self._build_trust_context()
            decision = self.zta_engine.evaluate_request("telemetry_read", ctx)
            if decision == AuthorizationDecision.DENY:
                # Do not emit telemetry if trust is too low
                return
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

            from vireon.plugins.ble.attacks import GATTCorruptionAttack, MalformedNotificationAttack
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
            except Exception:
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

        # 3.5 Biometric Authentication
        if self._simulation_context.get("biometric_auth", False) and self.biometric_gate:
            self.biometric_gate.authenticate_window(data_to_process, sample_rate)
            if self.biometric_gate.is_locked:
                print("[Coordinator] Egress blocked by BiometricGate.")
                return

        # 4. Push final data to LSL if active
        if self.lsl_streamer:
            lsl_data = data_to_process
            if self.privacy_filter is not None:
                lsl_data = self.privacy_filter.filter_signal(lsl_data.copy())
                if self.privacy_tracker:
                    self.privacy_tracker.consume(0.001)
                    
            if self.p300_analyzer is not None:
                leakage_report = self.p300_analyzer.scan_for_leakage(lsl_data)
                self.total_p300_leakage_events += leakage_report["p300_events_detected"]
                    
            self.lsl_streamer.push_eeg_chunk(lsl_data)
            
            active_attack = self._simulation_context.get("active_attack", "none")
            telemetry = {
                "sim_clock": self.engine.sim_clock,
                "niss_score": self.twin.niss_score,
                "hazard_state": self.twin.hazard_state,
                "iso_severity": self.twin.iso_severity,
                "temperature_celsius": self.twin.temperature_celsius,
                "active_attack": active_attack
            }
            
            # Map Active Attack to Threat Intel
            if self.threat_intel and active_attack != "none":
                tara_intel = self.threat_intel.resolve_attack(active_attack)
                if tara_intel:
                    telemetry["threat_intel"] = tara_intel
            
            if self.config.security.enabled and self.ids:
                telemetry["mean_confidence"] = self.ids.history_confidence[-1] if self.ids.history_confidence else 1.0
                
            if self._simulation_context.get("nsp_mode", False) and self.nsp_wrapper:
                telemetry = self.nsp_wrapper.encrypt_payload(telemetry)
                
            if self._simulation_context.get("e2ee_mode", False) and self.e2ee_channel:
                telemetry = {"e2ee_payload": self.e2ee_channel.encrypt_payload(telemetry)}
                
            self.lsl_streamer.push_telemetry(telemetry)
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
            
        summary["nsp_active"] = self._simulation_context.get("nsp_mode", False)
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
        print("=== NEUROSHIELD REPORTS ===")
        print(f"  - HTML Log:     {self.config.output.report_prefix}_report.html")
        print(f"  - PDF Report:   {self.config.output.report_prefix}_report.pdf")
        print(f"  - Markdown Log: {self.config.output.report_prefix}_report.md")
        print(f"  - JSON DB:      {self.config.output.report_prefix}_telemetry.json")
        print("=" * 60)
