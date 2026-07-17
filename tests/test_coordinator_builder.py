from unittest.mock import MagicMock, patch

from vireon.core.coordinator_builder import SimulationBuilder
from vireon.core.event_bus import EventBus

class MockConfigAttacks:
    def __init__(self):
        self.active = []
        self.target_channels = ["ch1"]
        self.noise_level_uv = 10.0
        self.drift_rate_uv_per_sec = 5.0
        self.spike_impedance_kohm = 50.0
        self.attenuation_factor = 0.5

class MockConfigDevice:
    def __init__(self):
        self.type = "test_device"
        self.serial_port = "/dev/null"

class MockConfigEmulation:
    def __init__(self):
        self.hardware_loopback = False
        self.ble = False
        self.ble_attack = "none"

class MockConfigDataset:
    def __init__(self):
        self.path = None

class MockConfigSecurity:
    def __init__(self):
        self.enabled = False

class MockConfigWeb:
    def __init__(self):
        self.port = 8080

class MockConfig:
    def __init__(self):
        self.attacks = MockConfigAttacks()
        self.device = MockConfigDevice()
        self.emulation = MockConfigEmulation()
        self.dataset = MockConfigDataset()
        self.security = MockConfigSecurity()
        self.web = MockConfigWeb()
        self.duration_sec = 10.0

def create_mock_coordinator():
    c = MagicMock()
    c.config = MockConfig()
    c.attack_engine = MagicMock()
    c.event_bus = EventBus()
    c.registry = MagicMock()
    c.twin = MagicMock()
    c.twin.num_channels = 2
    c.twin.sample_rate = 250
    c.link_guard = None
    c.ips = None
    c.engine = MagicMock()
    return c

def test_setup_attacks_noise():
    c = create_mock_coordinator()
    c.config.attacks.active = ["noise"]
    builder = SimulationBuilder(c)
    
    with patch("vireon.core.attack.NoiseInjectionAttack") as mock_attack:
        builder.setup_attacks()
        mock_attack.assert_called_once_with(["ch1"], 10.0)
        c.attack_engine.add_modifier.assert_called_once()

def test_setup_attacks_drift_impedance_suppression():
    c = create_mock_coordinator()
    c.config.attacks.active = ["drift", "impedance", "suppression"]
    builder = SimulationBuilder(c)
    
    with patch("vireon.core.attack.SignalDriftAttack"), \
         patch("vireon.core.attack.ImpedanceSpikeAttack"), \
         patch("vireon.core.attack.SignalSuppressionAttack"):
        builder.setup_attacks()
        assert c.attack_engine.add_modifier.call_count == 3

def test_setup_attacks_stimulation_leak_unsecured():
    c = create_mock_coordinator()
    c.config.attacks.active = ["stimulation_leak"]
    c.config.security.enabled = False
    builder = SimulationBuilder(c)
    
    with patch("vireon.plugins.clinical.closed_loop.UncontrolledStimulationAttack") as leak:
        builder.setup_attacks()
        leak.assert_called_once_with(c.twin)
        leak.return_value.apply.assert_called_once()

def test_setup_attacks_stimulation_leak_secured():
    c = create_mock_coordinator()
    c.config.attacks.active = ["stimulation_leak"]
    c.config.security.enabled = True
    builder = SimulationBuilder(c)
    
    with patch("vireon.core.detection.SecurityEngine"), \
         patch("vireon.core.clinical.NeuroIPS") as neuro_ips:
        neuro_ips.return_value.sanitize_stimulation_write.return_value = (5.0, 100.0)
        builder.setup_attacks()
        c.twin.update_therapy.assert_called_once_with(True)
        c.twin.update_stimulation_params.assert_called_once_with(5.0, 100.0)

def test_setup_device():
    c = create_mock_coordinator()
    c.registry.has.return_value = True
    builder = SimulationBuilder(c)
    
    device = builder.setup_device()
    c.registry.create.assert_called_once_with("devices", "test_device", serial_port="/dev/null")
    assert device == c.registry.create.return_value

def test_setup_device_unknown():
    c = create_mock_coordinator()
    c.registry.has.return_value = False
    builder = SimulationBuilder(c)
    
    device = builder.setup_device()
    c.registry.create.assert_not_called()
    assert device is None

def test_setup_dataset_hardware_loopback():
    c = create_mock_coordinator()
    c.config.emulation.hardware_loopback = True
    builder = SimulationBuilder(c)
    
    with patch("vireon.plugins.devices.hardware_bridge.HardwareBridge") as hb:
        reader = builder.setup_dataset()
        hb.assert_called_once_with(host="127.0.0.1", port=9090)
        hb.return_value.start.assert_called_once()
        assert reader == hb.return_value
        assert c.bridge == hb.return_value

def test_setup_dataset_edf():
    c = create_mock_coordinator()
    c.config.dataset.path = "test.edf"
    builder = SimulationBuilder(c)
    
    with patch("vireon.plugins.datasets.edf_reader.EDFReader") as edf:
        reader = builder.setup_dataset()
        edf.assert_called_once_with("test.edf")
        assert reader == edf.return_value

def test_setup_dataset_csv():
    c = create_mock_coordinator()
    c.config.dataset.path = "data.csv"
    builder = SimulationBuilder(c)
    
    with patch("vireon.plugins.datasets.csv_reader.CSVReader") as csv:
        reader = builder.setup_dataset()
        csv.assert_called_once_with("data.csv")
        assert reader == csv.return_value

def test_setup_lsl_streamer():
    c = create_mock_coordinator()
    builder = SimulationBuilder(c)
    
    with patch("vireon.core.lsl_streamer.LSLStreamer") as lsl:
        builder.setup_lsl_streamer()
        lsl.assert_called_once_with(num_channels=2, srate=250)
        assert c.lsl_streamer == lsl.return_value
        assert c.config.duration_sec == 100000.0

def test_setup_web_server():
    c = create_mock_coordinator()
    builder = SimulationBuilder(c)
    
    with patch("vireon.plugins.reports.web_server.start_web_server") as start_web, \
         patch("vireon.plugins.reports.ws_server.NeuroWebSocketServer") as ws_server:
        builder.setup_web_server()
        assert hasattr(c, "admin_token")
        assert hasattr(c, "view_token")
        start_web.assert_called_once()
        ws_server.assert_called_once()
        ws_server.return_value.start.assert_called_once()
        c.engine.add_callback.assert_called_once_with(c._ws_broadcast_callback)

def test_setup_ble():
    c = create_mock_coordinator()
    builder = SimulationBuilder(c)
    
    with patch("vireon.plugins.ble.emulator.VirtualBLEServer") as server, \
         patch("vireon.plugins.ble.emulator.VirtualBLELink") as link, \
         patch("vireon.plugins.ble.emulator.VirtualBLEClient") as client:
        builder.setup_ble()
        
        server.assert_called_once()
        link.assert_called_once_with(server.return_value)
        client.assert_called_once_with(link.return_value)
        
        client_instance = client.return_value
        client_instance.connect.assert_called_once()
        client_instance.pair.assert_called_once()
        client_instance.negotiate_mtu.assert_called_once_with(247)
        client_instance.enable_notifications.assert_called_once_with("FE8D", "2D30", True)

def test_setup_ble_mtu_abuse():
    c = create_mock_coordinator()
    c.config.emulation.ble_attack = "mtu_abuse"
    builder = SimulationBuilder(c)
    
    with patch("vireon.plugins.ble.emulator.VirtualBLEServer"), \
         patch("vireon.plugins.ble.emulator.VirtualBLELink"), \
         patch("vireon.plugins.ble.emulator.VirtualBLEClient") as client, \
         patch("vireon.plugins.ble.attacks.MTUAbuseAttack") as mtu_abuse:
        builder.setup_ble()
        client.return_value.negotiate_mtu.assert_called_once_with(5)
        mtu_abuse.assert_called_once()
        mtu_abuse.return_value.apply.assert_called_once()

def test_setup_ble_pairing_fail():
    c = create_mock_coordinator()
    c.config.emulation.ble_attack = "pairing_fail"
    builder = SimulationBuilder(c)
    
    with patch("vireon.plugins.ble.emulator.VirtualBLEServer"), \
         patch("vireon.plugins.ble.emulator.VirtualBLELink"), \
         patch("vireon.plugins.ble.emulator.VirtualBLEClient"), \
         patch("vireon.plugins.ble.attacks.PairingFailureAttack") as pairing_fail:
        builder.setup_ble()
        pairing_fail.assert_called_once()
        pairing_fail.return_value.apply.assert_called_once()

def test_setup_ble_with_link_guard():
    c = create_mock_coordinator()
    c.config.security.enabled = True
    c.link_guard = MagicMock()
    c.link_guard.verify_mtu.return_value = 247
    builder = SimulationBuilder(c)
    
    with patch("vireon.plugins.ble.emulator.VirtualBLEServer"), \
         patch("vireon.plugins.ble.emulator.VirtualBLELink"), \
         patch("vireon.plugins.ble.emulator.VirtualBLEClient") as client:
        builder.setup_ble()
        c.link_guard.verify_mtu.assert_called_once_with(247)
        client.return_value.negotiate_mtu.assert_called_once_with(247)
