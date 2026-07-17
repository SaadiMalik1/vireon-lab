import json
from vireon.mcp_server import mock_authenticate_session, get_available_plugins, run_simulation, _verify_capability

def test_mock_authenticate_session_patient():
    res_str = mock_authenticate_session("dummy_hash", "patient")
    res = json.loads(res_str)
    assert res.get("status") == "Authentication Successful"
    assert "session_token" in res
    
    token = res["session_token"]
    assert _verify_capability(token, "log.read") is True
    assert _verify_capability(token, "simulation.run") is False

def test_mock_authenticate_session_clinician_fail():
    res_str = mock_authenticate_session("dummy_hash", "clinician", "wrong_sig")
    res = json.loads(res_str)
    assert "error" in res

def test_mock_authenticate_session_clinician_success(monkeypatch):
    monkeypatch.setenv("CLINICIAN_PUB_KEY", "test_sig")
    res_str = mock_authenticate_session("dummy_hash", "clinician", "test_sig")
    res = json.loads(res_str)
    assert res.get("status") == "Authentication Successful"
    assert "session_token" in res
    
    token = res["session_token"]
    assert _verify_capability(token, "simulation.run") is True

def test_get_available_plugins():
    res_str = get_available_plugins()
    res = json.loads(res_str)
    assert "categories" in res

def test_run_simulation_no_auth():
    res_str = run_simulation("invalid_token")
    res = json.loads(res_str)
    assert "error" in res

def test_run_simulation_with_auth(monkeypatch):
    monkeypatch.setenv("CLINICIAN_PUB_KEY", "test_sig")
    res_str = mock_authenticate_session("dummy_hash", "clinician", "test_sig")
    res = json.loads(res_str)
    token = res["session_token"]

    sim_res_str = run_simulation(token, duration_sec=0.1)
    sim_res = json.loads(sim_res_str)
    assert sim_res.get("status") == "Simulation Complete"
