import numpy as np
from unittest.mock import MagicMock
import json
from vireon.core.coordinator_callbacks import CoordinatorCallbacks
from vireon.core.zta import AuthorizationDecision

class MockConfig:
    def __init__(self):
        self.security = MagicMock()
        self.emulation = MagicMock()

def create_mock_coordinator():
    c = MagicMock()
    c.config = MockConfig()
    c.twin.get_state.return_value = {"base_state": 1}
    c.twin.active_attack = "none"
    c.twin.nsp_mode = False
    c.twin.e2ee_mode = False
    c.twin.dbs_mode = False
    c.twin.secure_mode = False
    c.twin.simulate_adc_saturation.side_effect = lambda x: x
    
    c.ws_server = MagicMock()
    c.privacy_filter = None
    c.privacy_tracker = None
    c.threat_intel = None
    c.ids = None
    c.ips = None
    c.nsp_wrapper = None
    c.zta_engine = None
    c.scenario = None
    c.engine = MagicMock()
    c.engine.sim_clock = 1.0
    c.attack_engine = MagicMock()
    c.registry = MagicMock()
    c.dbs_controller = None
    c.ble_link = None
    c.ble_client = None
    c.clinical_sim = MagicMock()
    c.biometric_gate = None
    c.lsl_streamer = None
    c.event_bus = MagicMock()
    return c

def test_ws_broadcast_callback():
    c = create_mock_coordinator()
    callbacks = CoordinatorCallbacks(c)
    
    # Dummy data 2x10
    data = np.random.rand(2, 10)
    # Inject NaN to test NaN replacement
    data[1, 0] = np.nan
    
    callbacks.ws_broadcast_callback(data, ["ch1", "ch2"], 250)
    
    c.ws_server.broadcast_sync.assert_called_once()
    args, kwargs = c.ws_server.broadcast_sync.call_args
    state = json.loads(args[0])
    
    assert "signal_chunk" in state
    assert np.isnan(state["signal_chunk"][0]) is False
    assert state["signal_chunk"][0] == 0.0
    assert state["active_attack"] == "none"

def test_ws_broadcast_with_privacy_and_security():
    c = create_mock_coordinator()
    c.privacy_filter = MagicMock()
    c.privacy_filter.filter_signal.side_effect = lambda x: x
    c.privacy_tracker = MagicMock()
    
    c.twin.active_attack = "test_attack"
    c.threat_intel = MagicMock()
    c.threat_intel.resolve_attack.return_value = {"severity": "high"}
    
    c.ids = MagicMock()
    c.ids.detections = ["det1"]
    
    c.ips = MagicMock()
    c.ips.blocked_attacks_count = 5
    c.ips.clamping_active = True
    c.ips.blocked_mtu_abuses = 2
    
    c.twin.nsp_mode = True
    c.nsp_wrapper = MagicMock()
    c.nsp_wrapper.encrypt_payload.return_value = {"encrypted": True}
    
    callbacks = CoordinatorCallbacks(c)
    data = np.ones((2, 10))
    callbacks.ws_broadcast_callback(data, ["ch1", "ch2"], 250)
    
    c.ws_server.broadcast_sync.assert_called_once()
    c.privacy_filter.filter_signal.assert_called_once()
    c.privacy_tracker.consume.assert_called_once()
    c.nsp_wrapper.encrypt_payload.assert_called_once()

def test_build_trust_context():
    c = create_mock_coordinator()
    callbacks = CoordinatorCallbacks(c)
    
    c.biometric_gate = MagicMock()
    c.biometric_gate.is_locked = True
    ctx = callbacks.build_trust_context()
    assert ctx.biometric_confidence == 0.0
    
    c.biometric_gate.is_locked = False
    c.ids = MagicMock()
    c.ids.history_confidence = [0.8]
    ctx = callbacks.build_trust_context()
    assert ctx.biometric_confidence == 0.8

def test_simulation_callback_zta_deny():
    c = create_mock_coordinator()
    c.zta_engine = MagicMock()
    c.zta_engine.evaluate_request.return_value = AuthorizationDecision.DENY
    callbacks = CoordinatorCallbacks(c)
    
    data = np.ones((2, 10))
    callbacks.simulation_callback(data, ["ch1", "ch2"], 250)
    # Shouldn't proceed, verify something wasn't called
    c.twin.simulate_adc_saturation.assert_not_called()

def test_simulation_callback_basic_path():
    c = create_mock_coordinator()
    callbacks = CoordinatorCallbacks(c)
    
    data = np.ones((2, 10))
    callbacks.simulation_callback(data, ["ch1", "ch2"], 250)
    
    c.twin.simulate_adc_saturation.assert_called_once()
    c.clinical_sim.process_signal.assert_called_once()

def test_simulation_callback_dbs_mode():
    c = create_mock_coordinator()
    c.twin.dbs_mode = True
    c.dbs_controller = MagicMock()
    c.dbs_controller.lfp_generator.read_chunk.return_value = np.zeros((2, 10))
    c.ids = MagicMock()
    c.ids.analyze_clinical.return_value = ["anomaly1"]
    c.ips = MagicMock()
    c.twin.secure_mode = True
    
    callbacks = CoordinatorCallbacks(c)
    data = np.ones((2, 10))
    callbacks.simulation_callback(data, ["ch1", "ch2"], 250)
    
    c.dbs_controller.lfp_generator.read_chunk.assert_called_once()
    c.dbs_controller.process_lfp.assert_called_once()
    c.ids.analyze_clinical.assert_called_once()
    c.ips.mitigate_pathological_sync.assert_called_once()

def test_simulation_callback_ble_mode():
    c = create_mock_coordinator()
    c.config.emulation.ble = True
    c.config.emulation.ble_attack = "none"
    c.ble_link = MagicMock()
    c.ble_link.connected = True
    c.ble_link.mtu = 24
    c.ble_client = MagicMock()
    c.ble_client.received_packets = [b"a" * 160] # Dummy bytes to simulate reconstructed signal
    
    callbacks = CoordinatorCallbacks(c)
    data = np.ones((2, 10), dtype=np.float64)
    c.ble_client.received_packets = [data.tobytes()]
    
    callbacks.simulation_callback(data, ["ch1", "ch2"], 250)
    
    c.ble_client.receive_notification.assert_called_once()
    assert len(c.ble_client.received_packets) == 0 # It clears it
    c.clinical_sim.process_signal.assert_called_once()

def test_simulation_callback_lsl_streamer():
    c = create_mock_coordinator()
    c.lsl_streamer = MagicMock()
    c.privacy_filter = MagicMock()
    c.privacy_filter.filter_signal.side_effect = lambda x: x
    c.p300_analyzer = MagicMock()
    c.p300_analyzer.scan_for_leakage.return_value = {"p300_events_detected": 1}
    c.total_p300_leakage_events = 0
    c.ids = MagicMock()
    c.ids.history_confidence = [0.9]
    c.config.security.enabled = True
    
    callbacks = CoordinatorCallbacks(c)
    data = np.ones((2, 10))
    callbacks.simulation_callback(data, ["ch1", "ch2"], 250)
    
    c.lsl_streamer.push_eeg_chunk.assert_called_once()
    c.lsl_streamer.push_telemetry.assert_called_once()
    assert c.total_p300_leakage_events == 1
