import unittest
import http.client
import json
import time
import ssl
from vireon.core.twin import DigitalTwin
from vireon.core.attack import SignalAttackEngine
from vireon.plugins.reports.web_server import start_web_server, simulation_context

class TestWebUIRESTAPI(unittest.TestCase):
    def setUp(self):
        self.twin = DigitalTwin(num_channels=8)
        self.attack_engine = SignalAttackEngine(self.twin)
        # Bind server to port 8181 to avoid clashes
        self.server = start_web_server(self.twin, self.attack_engine, port=8181)
        time.sleep(0.1) # Wait for socket thread to bind

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def _get(self, path):
        """Helper: send GET and return (status, parsed_json)."""
        context = ssl._create_unverified_context()
        conn = http.client.HTTPSConnection('127.0.0.1', 8181, timeout=5, context=context)
        conn.request('GET', path)
        resp = conn.getresponse()
        status = resp.status
        data = json.loads(resp.read().decode('utf-8'))
        conn.close()
        return status, data

    def _post_json(self, path, payload_dict):
        """Helper: send POST with JSON body and return (status, parsed_json)."""
        body = json.dumps(payload_dict).encode('utf-8')
        context = ssl._create_unverified_context()
        conn = http.client.HTTPSConnection('127.0.0.1', 8181, timeout=5, context=context)
        conn.request('POST', path, body=body, headers={'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:8181'})
        resp = conn.getresponse()
        status = resp.status
        try:
            data = json.loads(resp.read().decode('utf-8'))
        except json.JSONDecodeError:
            data = {}
        conn.close()
        return status, data

    def test_get_api_state(self):
        status, data = self._get('/api/state')
        self.assertEqual(status, 200)
        self.assertEqual(data["device_id"], "virtual_openbci_board")
        self.assertTrue(data["connected"])

    def test_post_api_control_modes(self):
        status, data = self._post_json('/api/control', {"secure_mode": True, "dbs_mode": True})
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["context"]["secure_mode"])
        self.assertTrue(data["context"]["dbs_mode"])

        # Verify globals updated
        self.assertTrue(simulation_context["secure_mode"])
        self.assertTrue(simulation_context["dbs_mode"])

    def test_post_api_control_attacks(self):
        status, data = self._post_json('/api/control', {"active_attack": "noise"})
        self.assertEqual(status, 200)
        self.assertEqual(data["context"]["active_attack"], "noise")

        # Verify attack modifier added to engine
        self.assertEqual(len(self.attack_engine.modifiers), 1)
        self.assertEqual(simulation_context["active_attack"], "noise")

if __name__ == "__main__":
    unittest.main()
