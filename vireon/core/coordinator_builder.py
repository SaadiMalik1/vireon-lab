import os
import sys
import logging
from vireon.core.event_bus import Event

logger = logging.getLogger(__name__)

class SimulationBuilder:
    def __init__(self, coordinator):
        self.c = coordinator
        self.config = coordinator.config

    def setup_attacks(self):
        """Configure signal modifiers from config."""
        target_channels = self.config.attacks.target_channels

        for attack_name in self.config.attacks.active:
            if attack_name == "noise":
                print(f"[VIREON] Injecting Noise Attack (SD={self.config.attacks.noise_level_uv} uV)")
                from vireon.core.attack import NoiseInjectionAttack
                self.c.attack_engine.add_modifier(
                    NoiseInjectionAttack(target_channels, self.config.attacks.noise_level_uv)
                )
            elif attack_name == "drift":
                print("[VIREON] Injecting Signal Drift Attack")
                from vireon.core.attack import SignalDriftAttack
                self.c.attack_engine.add_modifier(
                    SignalDriftAttack(target_channels, self.config.attacks.drift_rate_uv_per_sec)
                )
            elif attack_name == "impedance":
                print("[VIREON] Injecting Impedance Spike Attack")
                from vireon.core.attack import ImpedanceSpikeAttack
                self.c.attack_engine.add_modifier(
                    ImpedanceSpikeAttack(target_channels, self.config.attacks.spike_impedance_kohm)
                )
            elif attack_name == "suppression":
                print("[VIREON] Injecting Signal Suppression Attack")
                from vireon.core.attack import SignalSuppressionAttack
                self.c.attack_engine.add_modifier(
                    SignalSuppressionAttack(target_channels, self.config.attacks.attenuation_factor)
                )
            elif attack_name == "stimulation_leak":
                print("[VIREON] Injecting Stimulation Leak Attack")
                if self.config.security.enabled:
                    from vireon.core.detection import SecurityEngine
                    from vireon.core.clinical import NeuroIPS
                    temp_ids = SecurityEngine(self.c.twin)
                    temp_ips = NeuroIPS(self.c.twin, temp_ids)
                    amp, freq = temp_ips.sanitize_stimulation_write(10.0, 130.0)
                    self.c.twin.update_therapy(True)
                    self.c.twin.update_stimulation_params(amp, freq)
                else:
                    from vireon.plugins.clinical.closed_loop import UncontrolledStimulationAttack
                    leak = UncontrolledStimulationAttack(self.c.twin)
                    leak.apply()
            else:
                print(f"[VIREON] Warning: Unknown attack type: {attack_name}")

        self.c.event_bus.publish(Event(
            topic="attack.configured",
            data={"attacks": self.config.attacks.active},
            source="coordinator"
        ))

    def setup_device(self):
        """Load device wrapper from config."""
        device_wrapper = None
        try:
            if self.c.registry.has("devices", self.config.device.type):
                device_wrapper = self.c.registry.create(
                    "devices", 
                    self.config.device.type,
                    serial_port=self.config.device.serial_port
                )
            else:
                print(f"[VIREON] Warning: Unknown device type '{self.config.device.type}'")
        except Exception as e:
            logger.error(f"Error loading device module: {e}", exc_info=True)
            sys.exit(1)
        return device_wrapper

    def setup_dataset(self):
        """Load dataset reader from config."""
        dataset_reader = None

        if self.config.emulation.hardware_loopback:
            print("[VIREON] Configuring Hardware-in-the-loop (HIL) Socket Bridge...")
            from vireon.plugins.devices.hardware_bridge import HardwareBridge
            self.c.bridge = HardwareBridge(host="127.0.0.1", port=9090)
            self.c.bridge.start()
            dataset_reader = self.c.bridge
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

    def setup_lsl_streamer(self):
        """Initialize LSL Streamer."""
        print("[VIREON] Starting headless mode for automated testing. Initializing LSL Streamer...")
        try:
            from vireon.core.lsl_streamer import LSLStreamer
            self.c.lsl_streamer = LSLStreamer(num_channels=self.c.twin.num_channels, srate=self.c.twin.sample_rate)
            self.config.duration_sec = 100000.0  # Run indefinitely in LSL mode
        except Exception as e:
            logger.error(f"Failed to start LSL Streamer: {e}", exc_info=True)
            raise RuntimeError(f"LSL Streamer failed to initialize: {e}") from e

    def setup_web_server(self):
        """Start the Web UI dashboard."""
        import secrets
        from vireon.plugins.reports.web_server import start_web_server
        
        self.c.admin_token = secrets.token_urlsafe(16)
        self.c.view_token = secrets.token_urlsafe(16)

        self.c.web_server = start_web_server(
            twin=self.c.twin,
            attack_engine=self.c.attack_engine,
            port=self.config.web.port,
            ips=self.c.ips,
            link_guard=self.c.link_guard,
            admin_token=self.c.admin_token,
            view_token=self.c.view_token
        )
        
        self.c.web_server.simulation_context["secure_mode"] = self.config.security.enabled
        self.c.web_server.simulation_context["hardware_mode"] = self.config.emulation.hardware_loopback
        
        from vireon.plugins.reports.ws_server import NeuroWebSocketServer
        self.c.ws_server = NeuroWebSocketServer(port=self.config.web.port + 1, admin_token=self.c.admin_token, view_token=self.c.view_token)
        self.c.ws_server.start()

        self.c.engine.add_callback(self.c._ws_broadcast_callback)

    def setup_ble(self):
        """Initialize BLE emulation stack."""
        from vireon.plugins.ble.emulator import VirtualBLEServer, VirtualBLELink, VirtualBLEClient
        from vireon.plugins.ble.attacks import PairingFailureAttack, MTUAbuseAttack

        print("[VIREON] Initializing Virtual BLE Stack...")
        self.c.ble_server = VirtualBLEServer()
        self.c.ble_link = VirtualBLELink(self.c.ble_server)
        self.c.ble_client = VirtualBLEClient(self.c.ble_link)

        self.c.ble_client.connect()
        self.c.ble_client.pair(self.c.ble_link.pairing_code)

        requested_mtu = 247
        if self.config.emulation.ble_attack == "mtu_abuse":
            requested_mtu = 5
        if self.config.security.enabled and self.c.link_guard:
            requested_mtu = self.c.link_guard.verify_mtu(requested_mtu)
        self.c.ble_client.negotiate_mtu(requested_mtu)
        self.c.ble_client.enable_notifications("FE8D", "2D30", True)

        if self.config.emulation.ble_attack == "pairing_fail":
            PairingFailureAttack(self.c.twin).apply(self.c.ble_client, self.c.ble_link)
        elif self.config.emulation.ble_attack == "mtu_abuse" and not self.config.security.enabled:
            MTUAbuseAttack(self.c.twin, abnormal_mtu=5).apply(self.c.ble_client, self.c.ble_link)
