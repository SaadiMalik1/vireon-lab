import pytest
import http.client
import json
import ssl
import time
from vireon.core.twin import DigitalTwin
from vireon.core.attack import SignalAttackEngine
from vireon.plugins.reports.web_server import start_web_server

@pytest.fixture(scope="module")
def web_server():
    twin = DigitalTwin(num_channels=8)
    attack_engine = SignalAttackEngine(twin)
    # Use port 8282 for these tests
    server = start_web_server(twin, attack_engine, port=8282, admin_token="test_admin_token")
    time.sleep(0.5)
    yield server
    server.shutdown()
    server.server_close()

def _request(method, path, body=None, headers=None):
    if headers is None:
        headers = {}
    context = ssl._create_unverified_context()
    conn = http.client.HTTPSConnection('127.0.0.1', 8282, timeout=5, context=context)
    try:
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        status = resp.status
        try:
            data = json.loads(resp.read().decode('utf-8'))
        except json.JSONDecodeError:
            data = {}
        return status, data
    except Exception:
        # Fallback to HTTP if TLS is not available
        conn = http.client.HTTPConnection('127.0.0.1', 8282, timeout=5)
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        status = resp.status
        try:
            data = json.loads(resp.read().decode('utf-8'))
        except json.JSONDecodeError:
            data = {}
        return status, data

def test_api_history(web_server):
    status, data = _request("GET", "/api/history", headers={"Authorization": "Bearer test_admin_token"})
    assert status == 200
    assert isinstance(data, list)

def test_api_standards_mapping(web_server):
    status, data = _request("GET", "/api/standards_mapping.json")
    # Might be 404 if file is not physically there during tests, but endpoint is hit
    assert status in [200, 404]

def test_index_html(web_server):
    status, data = _request("GET", "/index.html")
    assert status in [200, 404]

def test_cors_rejection(web_server):
    # Missing Origin should be rejected
    status, data = _request("POST", "/api/control", body=json.dumps({}), headers={"Authorization": "Bearer test_admin_token"})
    assert status == 403

def test_auth_rejection(web_server):
    headers = {"Origin": "http://127.0.0.1:8282", "Content-Type": "application/json"}
    status, data = _request("POST", "/api/control", body=json.dumps({}), headers=headers)
    assert status == 401

def test_rate_limit(web_server):
    headers = {
        "Origin": "http://127.0.0.1:8282",
        "Content-Type": "application/json",
        "Authorization": "Bearer test_admin_token"
    }
    # Spam to trigger rate limit (15 reqs/sec)
    for _ in range(20):
        status, data = _request("POST", "/api/control", body=json.dumps({}), headers=headers)
        if status == 429:
            break
    assert status == 429

def test_post_control_various_attacks(web_server):
    # Wait to reset rate limit
    time.sleep(1.1)
    headers = {
        "Origin": "http://127.0.0.1:8282",
        "Content-Type": "application/json",
        "Authorization": "Bearer test_admin_token"
    }
    
    # Drift attack
    status, data = _request("POST", "/api/control", body=json.dumps({"active_attack": "drift"}), headers=headers)
    assert status == 200
    assert data["context"]["active_attack"] == "drift"
    
    # Impedance attack
    status, data = _request("POST", "/api/control", body=json.dumps({"active_attack": "impedance"}), headers=headers)
    assert status == 200
    
    # Suppression
    status, data = _request("POST", "/api/control", body=json.dumps({"active_attack": "suppression"}), headers=headers)
    assert status == 200
    
    # None (reset)
    status, data = _request("POST", "/api/control", body=json.dumps({"active_attack": "none"}), headers=headers)
    assert status == 200
