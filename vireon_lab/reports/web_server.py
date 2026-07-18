# Copyright 2026 VIREON Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
WARNING: This module is for simulation purposes only.
The web server binds to 0.0.0.0 without TLS. The trust boundary between the 
simulation and the host network is undefined. It relies on simplified CORS 
and rate limiting. Do not use for real clinical data.
"""
import http.server
import socketserver
import threading
import json
import os
import urllib.parse
import time
import subprocess
import ssl
from typing import Dict, Any
from vireon.core.attack import SignalAttackEngine, NoiseInjectionAttack, SignalDriftAttack, ImpedanceSpikeAttack, SignalSuppressionAttack
from vireon.core.protocol import RFFrameProcessor
from vireon.core.detection import SecurityEngine
from vireon_lab.reference_providers.clinical import NeuroIPS
from vireon.core.attack_factory import AttackFactory
from vireon_lab.providers.clinical.closed_loop import UncontrolledStimulationAttack
from vireon.core.twin import DigitalTwin
class BCIAPIRequestHandler(http.server.SimpleHTTPRequestHandler):
    server: 'ThreadedHTTPServer'
    
    @property
    def twin(self): return self.server.twin
    @property
    def attack_engine(self): return self.server.attack_engine
    @property
    def ips(self): return self.server.ips
    @property
    def link_guard(self): return self.server.link_guard
    @property
    def web_dir(self): return self.server.web_dir
    @property
    def simulation_context(self): return self.server.simulation_context

    @property
    def _rate_limit_lock(self): return self.server._rate_limit_lock
    @property
    def _ip_timestamps(self): return self.server._ip_timestamps
    @property
    def next_seq_no(self): return self.server.next_seq_no
    @next_seq_no.setter
    def next_seq_no(self, value): self.server.next_seq_no = value

    def get_processor(self):
        if self.server.frame_processor is None:
            self.server.frame_processor = RFFrameProcessor(b"X"*32)
        return self.server.frame_processor

    def translate_path(self, path):
        # Serve static files from the custom web folder
        parsed_url = urllib.parse.urlparse(path)
        unquoted_path = urllib.parse.unquote(parsed_url.path)
        rel_path = unquoted_path.lstrip('/')
        
        # Default to index.html
        if rel_path == "":
            rel_path = "index.html"
            
        full_path = os.path.abspath(os.path.join(self.web_dir, rel_path))
        # Prevent path traversal attacks by validating final absolute path with trailing separator
        safe_dir = os.path.abspath(self.web_dir)
        if not safe_dir.endswith(os.sep):
            safe_dir += os.sep
            
        if not full_path.startswith(safe_dir) and full_path != os.path.abspath(self.web_dir):
            return ""
            
        return full_path

    def _check_cors(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin or (not origin.startswith("http://localhost:") and not origin.startswith("http://127.0.0.1:")):
            self.send_error(403, "Forbidden CORS origin: Missing or unauthorized Origin header")
            return False
        return True

    def _check_rate_limit(self) -> bool:
        client_ip = self.client_address[0]
        now = time.time()
        
        with self._rate_limit_lock:
            # Prevent OOM from IP spoofing / botnets
            if len(self._ip_timestamps) > 1000:
                # Prune stale IPs that haven't made a request in the last 2 seconds
                stale_ips = [ip for ip, ts in self._ip_timestamps.items() if not ts or (now - ts[-1] > 2.0)]
                for ip in stale_ips:
                    del self._ip_timestamps[ip]

            if client_ip not in self._ip_timestamps:
                self._ip_timestamps[client_ip] = []
                
            # Filter timestamps in the last 1.0 seconds
            timestamps = [t for t in self._ip_timestamps[client_ip] if now - t < 1.0]
            
            if len(timestamps) >= 15: # Max 15 requests per second
                self.send_error(429, "Too Many Requests - Backend Rate Limit Exceeded")
                return False
                
            timestamps.append(now)
            self._ip_timestamps[client_ip] = timestamps
            
        return True

    def _check_auth(self, require_admin: bool = False) -> bool:
        auth_header = self.headers.get("Authorization")
        
        admin_token = self.simulation_context.get("admin_token")
        view_token = self.simulation_context.get("view_token")
        
        if not admin_token and not view_token:
            return True
            
        if not auth_header or not auth_header.startswith("Bearer "):
            self.send_error(401, "Unauthorized: Bearer token required")
            return False
            
        token = auth_header.split(" ")[1]
        
        if require_admin:
            if token != admin_token:
                self.send_error(403, "Forbidden: Admin token required for this operation")
                return False
            return True
            
        if token != admin_token and token != view_token:
            self.send_error(401, "Unauthorized: Invalid token")
            return False
            
        return True

    def do_GET(self):
        if self.path == "/api/state":
            if not self._check_auth():
                return
            state = self.twin.get_state()
            if self.ips:
                state["blocked_attacks_count"] = self.ips.blocked_attacks_count
                state["clamping_active"] = self.ips.clamping_active
                state["blocked_mtu_abuses"] = self.link_guard.blocked_mtu_abuses if self.link_guard else 0
                state["tissue_damage_risk"] = self.ips.ids.tissue_damage_risk if self.ips.ids else "NONE"
            else:
                state["blocked_attacks_count"] = 0
                state["clamping_active"] = False
                state["blocked_mtu_abuses"] = 0
                
            self.send_json(state)
        elif self.path == "/api/history":
            if not self._check_auth():
                return
            self.send_json(self.twin.get_history())
        elif self.path == "/api/standards_mapping.json":
            mapping_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "core", "data", "standards_mapping.json")
            if os.path.exists(mapping_path):
                with open(mapping_path, "r", encoding="utf-8") as f:
                    bundle = json.load(f)
                self.send_json(bundle)
            else:
                self.send_error(404, "Standards mapping bundle not found")
        elif self.path == "/" or self.path == "/index.html":
            # Inject WS Token dynamically into index.html
            full_path = self.translate_path(self.path)
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                content = content.replace("WS_TOKEN_PLACEHOLDER", self.simulation_context.get("admin_token", ""))
                content_bytes = content.encode("utf-8")
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.send_header('Content-Length', str(len(content_bytes)))
                self.end_headers()
                self.wfile.write(content_bytes)
            else:
                self.send_error(404, "index.html not found")
        else:
            # Fall back to serving static files
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/control":
            if not self._check_cors() or not self._check_rate_limit() or not self._check_auth(require_admin=True):
                return
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                params = json.loads(post_data.decode('utf-8'))
                
                # Simulate telemetry frame packet serialization & transmission
                processor = self.get_processor()
                payload_bytes = json.dumps(params).encode('utf-8')
                
                # Check if secure mode is enabled
                secure = self.simulation_context.get("secure_mode", False)
                
                # Pack the frame (transmitter side)
                frame = processor.pack_frame(self.next_seq_no, payload_type=0x01, payload=payload_bytes, secure_mode=secure)
                self.next_seq_no += 1
                
                # Process the frame (receiver/firmware side)
                seq, ptype, unpacked_payload = processor.unpack_frame(
                    frame, secure_mode=secure, current_time=self.twin.get_sim_clock()
                )
                validated_params = json.loads(unpacked_payload.decode('utf-8'))
                
                self._update_simulation(validated_params)
                self.send_json({"status": "success", "context": self.simulation_context})
            except Exception as e:
                # Log protocol violations in security IPS
                if "ProtocolError" in e.__class__.__name__ or "replay" in str(e).lower() or "signature" in str(e).lower() or "CRC" in str(e):
                    if self.ips is not None:
                        self.ips.blocked_attacks_count += 1
                self.send_error(400, f"Bad Request: {e}")
        elif self.path == "/api/neuro_dsl/compile":
            if not self._check_cors() or not self._check_rate_limit() or not self._check_auth(require_admin=True):
                return
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                params = json.loads(post_data.decode('utf-8'))
                source_code = params.get("source", "")
                
                # Resolve the correct path dynamically relative to this file
                dsl_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../neuro_dsl"))
                cmd = ["cargo", "run", "--bin", "forge"]
                
                from vireon.sdk.runner import run_sandboxed
                result = run_sandboxed(
                    cmd, 
                    input_data=source_code, 
                    cwd=dsl_dir
                )
                
                if result.returncode != 0:
                    self.send_json({"status": "error", "error": result.stderr})
                else:
                    hex_bytecode = result.stdout.strip()
                    # Trigger a benign coherence test via twin
                    self.twin.update_stimulation_params(5.0, 130.0) # Active stim
                    self.twin.autonomic_pupil_dilation_mm = 4.5 # Coherent response
                    
                    self.send_json({"status": "success", "bytecode": hex_bytecode})
            except Exception as e:
                self.send_error(400, f"Bad Request: {e}")
        else:
            self.send_error(404, "Not Found")

    def send_json(self, data: Any):
        response_bytes = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_bytes)))
        # Disable caching for API responses
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(response_bytes)

    def _update_simulation(self, params: Dict[str, Any]):
        with self.server.context_lock:
            # 0. Update custom slider value overrides in context
            if "noise_intensity" in params:
                self.simulation_context["noise_intensity"] = float(params["noise_intensity"])
            if "attenuation_factor" in params:
                self.simulation_context["attenuation_factor"] = float(params["attenuation_factor"])
            if "impedance_kohm" in params:
                self.simulation_context["impedance_kohm"] = float(params["impedance_kohm"])
                
            # Update live digital twin parameter overrides
            if "battery_level" in params:
                self.twin.battery_level = float(params["battery_level"])
            
        if "stimulation_amplitude_ma" in params or "stimulation_frequency_hz" in params:
            amp = float(params.get("stimulation_amplitude_ma", self.twin.stimulation_amplitude_ma))
            freq = float(params.get("stimulation_frequency_hz", self.twin.stimulation_frequency_hz))
            
            # Sanitization ceiling clamp check under security shield
            if self.simulation_context["secure_mode"]:
                if self.ips is not None:
                    amp, freq = self.ips.sanitize_stimulation_write(amp, freq)
                else:
                    temp_ids = SecurityEngine(self.twin)
                    temp_ips = NeuroIPS(self.twin, temp_ids)
                    amp, freq = temp_ips.sanitize_stimulation_write(amp, freq)
                
            self.twin.update_therapy(amp > 0.0)
            self.twin.update_stimulation_params(amp, freq)
            
        # 1. Update Mode states
        if "dbs_mode" in params:
            self.simulation_context["dbs_mode"] = bool(params["dbs_mode"])
            self.twin.dbs_mode = self.simulation_context["dbs_mode"]
        if "secure_mode" in params:
            self.simulation_context["secure_mode"] = bool(params["secure_mode"])
            self.twin.secure_mode = self.simulation_context["secure_mode"]
        if "nsp_mode" in params:
            self.simulation_context["nsp_mode"] = bool(params["nsp_mode"])
            self.twin.nsp_mode = self.simulation_context["nsp_mode"]
        if "hardware_mode" in params:
            hw_mode = bool(params["hardware_mode"])
            self.simulation_context["hardware_mode"] = hw_mode
            self.twin.hardware_mode = hw_mode
            
        # 2. Update Attack configuration
        if "active_attack" in params or "noise_intensity" in params or "attenuation_factor" in params or "impedance_kohm" in params:
            if "active_attack" in params:
                attack_type = str(params["active_attack"]).lower()
                self.simulation_context["active_attack"] = attack_type
                self.twin.active_attack = attack_type
            else:
                attack_type = str(self.simulation_context["active_attack"])
                self.twin.active_attack = attack_type
            
            # Clear existing signal modifiers
            with self.attack_engine.lock if hasattr(self.attack_engine, 'lock') else threading.Lock():
                self.attack_engine.modifiers.clear()
                
                # Apply new signal attacks using current context intensity values
                if attack_type not in ["noise", "drift", "impedance", "suppression", "none", "", "phase_shift", "stimulation_leak"]:
                    try:
                        dynamic_attack = AttackFactory.create_dynamic_attack(attack_type, target_channels=[0, 1])
                        self.attack_engine.add_modifier(dynamic_attack)
                    except ValueError as e:
                        print(f"Error loading standard attack: {e}")
                elif attack_type == "noise":
                    self.attack_engine.add_modifier(NoiseInjectionAttack([0, 1], noise_level_microvolts=float(self.simulation_context["noise_intensity"])))
                elif attack_type == "drift":
                    self.attack_engine.add_modifier(SignalDriftAttack([0, 1], drift_rate_uv_per_sec=10.0))
                elif attack_type == "impedance":
                    self.attack_engine.add_modifier(ImpedanceSpikeAttack([0, 1], spike_value_kohm=float(self.simulation_context["impedance_kohm"])))
                elif attack_type == "suppression":
                    self.attack_engine.add_modifier(SignalSuppressionAttack([0, 1], attenuation_factor=float(self.simulation_context["attenuation_factor"])))
                    
            # Update DBS attacks
            if attack_type == "phase_shift":
                self.simulation_context["dbs_attack"] = "phase_shift"
            else:
                self.simulation_context["dbs_attack"] = ""
                
            # If stimulation leak is chosen and secure mode is NOT active, trigger it immediately
            if attack_type == "stimulation_leak":
                if not self.simulation_context["secure_mode"]:
                    leak = UncontrolledStimulationAttack(self.twin)
                    leak.apply()
                else:
                    # If secure mode is active, clamp it safely
                    temp_ids = SecurityEngine(self.twin)
                    temp_ips = NeuroIPS(self.twin, temp_ids)
                    amp, freq = temp_ips.sanitize_stimulation_write(10.0, 130.0)
                    self.twin.update_therapy(True)
                    self.twin.update_stimulation_params(amp, freq)
                    
            # If reset/none is chosen, reset the alerts and alarms
            if attack_type == "none" or attack_type == "":
                self.twin.set_clinical_alert(False, "Nominal")
                self.twin.update_clinical_risk("NOMINAL", "NEGLIGIBLE", "NONE", "MONITOR")
                self.twin.update_decoder_confidence(1.0)
                self.twin.update_impedance(0, 5.0)
                self.twin.update_impedance(1, 5.0)
                self.twin.update_therapy(False)
                self.twin.update_stimulation_params(0.0, 0.0)

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Multiple threads handling client requests concurrently."""
    daemon_threads = True
    twin: DigitalTwin
    attack_engine: SignalAttackEngine
    ips: Any
    link_guard: Any
    frame_processor: Any
    next_seq_no: int
    _rate_limit_lock: threading.Lock
    _ip_timestamps: Dict[str, list[float]]
    context_lock: threading.Lock
    simulation_context: Dict[str, Any]
    web_dir: str

def start_web_server(twin: DigitalTwin, attack_engine: SignalAttackEngine, port: int = 7777, ips = None, link_guard = None, admin_token: str = "", view_token: str = "") -> ThreadedHTTPServer:
    server = ThreadedHTTPServer(("127.0.0.1", port), BCIAPIRequestHandler)
    
    server.twin = twin
    server.attack_engine = attack_engine
    server.ips = ips
    server.link_guard = link_guard
    server.frame_processor = None
    server.next_seq_no = 0
    server._rate_limit_lock = threading.Lock()
    server._ip_timestamps = {}
    server.context_lock = threading.Lock()
    server.simulation_context = {
        "dbs_mode": False,
        "secure_mode": False,
        "nsp_mode": False,
        "hardware_mode": False,
        "dbs_attack": "", 
        "active_attack": "none", 
        "noise_intensity": 50.0,
        "attenuation_factor": 0.1,
        "impedance_kohm": 60.0,
        "admin_token": admin_token,
        "view_token": view_token
    }
    
    # Sync initial state to twin
    twin.dbs_mode = server.simulation_context.get("dbs_mode", False)
    twin.secure_mode = server.simulation_context.get("secure_mode", False)
    twin.nsp_mode = server.simulation_context.get("nsp_mode", False)
    twin.hardware_mode = server.simulation_context.get("hardware_mode", False)
    twin.active_attack = server.simulation_context.get("active_attack", "none")
    
    # Resolve index.html target directories
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server.web_dir = os.path.join(current_dir, "web")
    
    cert_file = os.path.join(current_dir, "cert.pem")
    key_file = os.path.join(current_dir, "key.pem")
    
    # Generate self-signed cert if missing
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print("[WebServer] Generating self-signed TLS certificate for localhost...")
        try:
            subprocess.run([
                "openssl", "req", "-x509", "-newkey", "rsa:4096", "-nodes",
                "-out", cert_file, "-keyout", key_file, "-days", "365",
                "-subj", "/CN=127.0.0.1"
            ], check=True, capture_output=True)
        except Exception as e:
            print(f"[WebServer] Failed to generate TLS cert: {e}. Falling back to HTTP.")
            
    if os.path.exists(cert_file) and os.path.exists(key_file):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        print(f"[WebServer] TLS enabled on https://127.0.0.1:{port}")
    else:
        print(f"[WebServer] Running on http://127.0.0.1:{port}")
    
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    return server
