import http.server
import socketserver
import threading
import json
import os
import urllib.parse
from typing import Dict, Any
from vireon.core.twin import DigitalTwin
from vireon.core.attack import SignalAttackEngine, NoiseInjectionAttack, SignalDriftAttack, ImpedanceSpikeAttack, SignalSuppressionAttack

# Shared context containing active web controls
simulation_context = {
    "dbs_mode": False,
    "secure_mode": False,
    "nsp_mode": False,
    "hardware_mode": False,
    "dbs_attack": "", # "", "phase_shift"
    "active_attack": "none", # "none", or standard internal identifier
    "noise_intensity": 50.0,
    "attenuation_factor": 0.1,
    "impedance_kohm": 60.0,
    "ws_token": "" # Populated on launch for WS auth
}

class BCIAPIRequestHandler(http.server.SimpleHTTPRequestHandler):
    # Class variables set during initialization
    twin: DigitalTwin = None
    attack_engine: SignalAttackEngine = None
    ips = None
    link_guard = None
    web_dir: str = ""
    
    frame_processor = None
    next_seq_no = 0

    _rate_limit_lock = threading.Lock()
    _ip_timestamps = {}

    @classmethod
    def get_processor(cls):
        if cls.frame_processor is None:
            from vireon.core.protocol import RFFrameProcessor
            cls.frame_processor = RFFrameProcessor()
        return cls.frame_processor

    def translate_path(self, path):
        # Serve static files from the custom web folder
        parsed_url = urllib.parse.urlparse(path)
        rel_path = parsed_url.path.lstrip('/')
        
        # Prevent path traversal attacks
        if ".." in rel_path or rel_path.startswith('/'):
            return ""

        # Default to index.html
        if rel_path == "":
            rel_path = "index.html"
            
        full_path = os.path.join(self.web_dir, rel_path)
        return full_path

    def _check_cors(self) -> bool:
        origin = self.headers.get("Origin")
        if origin and not origin.startswith("http://localhost:") and not origin.startswith("http://127.0.0.1:"):
            self.send_error(403, "Forbidden CORS origin")
            return False
        return True

    def _check_rate_limit(self) -> bool:
        import time
        client_ip = self.client_address[0]
        now = time.time()
        
        with BCIAPIRequestHandler._rate_limit_lock:
            # Prevent OOM from IP spoofing / botnets
            if len(BCIAPIRequestHandler._ip_timestamps) > 1000:
                # Prune stale IPs that haven't made a request in the last 2 seconds
                stale_ips = [ip for ip, ts in BCIAPIRequestHandler._ip_timestamps.items() if not ts or (now - ts[-1] > 2.0)]
                for ip in stale_ips:
                    del BCIAPIRequestHandler._ip_timestamps[ip]

            if client_ip not in BCIAPIRequestHandler._ip_timestamps:
                BCIAPIRequestHandler._ip_timestamps[client_ip] = []
                
            # Filter timestamps in the last 1.0 seconds
            timestamps = [t for t in BCIAPIRequestHandler._ip_timestamps[client_ip] if now - t < 1.0]
            
            if len(timestamps) >= 15: # Max 15 requests per second
                self.send_error(429, "Too Many Requests - Backend Rate Limit Exceeded")
                return False
                
            timestamps.append(now)
            BCIAPIRequestHandler._ip_timestamps[client_ip] = timestamps
            
        return True

    def do_GET(self):
        if self.path == "/api/state":
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
                content = content.replace("WS_TOKEN_PLACEHOLDER", simulation_context.get("ws_token", ""))
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
            if not self._check_cors() or not self._check_rate_limit():
                return
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                params = json.loads(post_data.decode('utf-8'))
                
                # Simulate telemetry frame packet serialization & transmission
                processor = self.get_processor()
                payload_bytes = json.dumps(params).encode('utf-8')
                
                # Check if secure mode is enabled
                secure = simulation_context.get("secure_mode", False)
                
                # Pack the frame (transmitter side)
                frame = processor.pack_frame(BCIAPIRequestHandler.next_seq_no, payload_type=0x01, payload=payload_bytes, secure_mode=secure)
                BCIAPIRequestHandler.next_seq_no += 1
                
                # Process the frame (receiver/firmware side)
                seq, ptype, unpacked_payload = processor.unpack_frame(
                    frame, secure_mode=secure, current_time=self.twin.get_sim_clock()
                )
                validated_params = json.loads(unpacked_payload.decode('utf-8'))
                
                self._update_simulation(validated_params)
                self.send_json({"status": "success", "context": simulation_context})
            except Exception as e:
                # Log protocol violations in security IPS
                if "ProtocolError" in e.__class__.__name__ or "replay" in str(e).lower() or "signature" in str(e).lower() or "CRC" in str(e):
                    if self.ips is not None:
                        self.ips.blocked_attacks_count += 1
                self.send_error(400, f"Bad Request: {e}")
        elif self.path == "/api/runemate/compile":
            if not self._check_cors() or not self._check_rate_limit():
                return
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                params = json.loads(post_data.decode('utf-8'))
                source_code = params.get("source", "")
                
                # Execute runemate forge compiler
                import subprocess
                # Write to temp file
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                    f.write(source_code)
                    tmp_name = f.name
                    
                cmd = f"cargo run --bin forge < {tmp_name}"
                result = subprocess.run(cmd, shell=True, cwd="/home/ronin/Documents/n2/runemate", capture_output=True, text=True)
                os.unlink(tmp_name)
                
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
        global simulation_context
        
        # 0. Update custom slider value overrides in context
        if "noise_intensity" in params:
            simulation_context["noise_intensity"] = float(params["noise_intensity"])
        if "attenuation_factor" in params:
            simulation_context["attenuation_factor"] = float(params["attenuation_factor"])
        if "impedance_kohm" in params:
            simulation_context["impedance_kohm"] = float(params["impedance_kohm"])
            
        # Update live digital twin parameter overrides
        if "battery_level" in params:
            self.twin.battery_level = float(params["battery_level"])
            
        if "stimulation_amplitude_ma" in params or "stimulation_frequency_hz" in params:
            amp = float(params.get("stimulation_amplitude_ma", self.twin.stimulation_amplitude_ma))
            freq = float(params.get("stimulation_frequency_hz", self.twin.stimulation_frequency_hz))
            
            # Sanitization ceiling clamp check under security shield
            if simulation_context["secure_mode"]:
                if self.ips is not None:
                    amp, freq = self.ips.sanitize_stimulation_write(amp, freq)
                else:
                    from vireon.core.security import NeuroSignalAssuranceEngine, NeuroIPS
                    temp_ids = NeuroSignalAssuranceEngine(self.twin)
                    temp_ips = NeuroIPS(self.twin, temp_ids)
                    amp, freq = temp_ips.sanitize_stimulation_write(amp, freq)
                
            self.twin.update_therapy(amp > 0.0)
            self.twin.update_stimulation_params(amp, freq)
            
        # 1. Update Mode states
        if "dbs_mode" in params:
            simulation_context["dbs_mode"] = bool(params["dbs_mode"])
        if "secure_mode" in params:
            simulation_context["secure_mode"] = bool(params["secure_mode"])
        if "nsp_mode" in params:
            simulation_context["nsp_mode"] = bool(params["nsp_mode"])
        if "hardware_mode" in params:
            hw_mode = bool(params["hardware_mode"])
            simulation_context["hardware_mode"] = hw_mode
            self.twin.hardware_mode = hw_mode
            
        # 2. Update Attack configuration
        if "active_attack" in params or "noise_intensity" in params or "attenuation_factor" in params or "impedance_kohm" in params:
            if "active_attack" in params:
                attack_type = str(params["active_attack"]).lower()
                simulation_context["active_attack"] = attack_type
            else:
                attack_type = simulation_context["active_attack"]
            
            # Clear existing signal modifiers
            with self.attack_engine.lock if hasattr(self.attack_engine, 'lock') else threading.Lock():
                self.attack_engine.modifiers.clear()
                
                # Apply new signal attacks using current context intensity values
                if attack_type not in ["noise", "drift", "impedance", "suppression", "none", "", "phase_shift", "stimulation_leak"]:
                    from vireon.core.attack_factory import AttackFactory
                    try:
                        dynamic_attack = AttackFactory.create_dynamic_attack(attack_type, target_channels=[0, 1])
                        self.attack_engine.add_modifier(dynamic_attack)
                    except ValueError as e:
                        print(f"Error loading standard attack: {e}")
                elif attack_type == "noise":
                    self.attack_engine.add_modifier(NoiseInjectionAttack([0, 1], noise_level_microvolts=simulation_context["noise_intensity"]))
                elif attack_type == "drift":
                    self.attack_engine.add_modifier(SignalDriftAttack([0, 1], rate=10.0))
                elif attack_type == "impedance":
                    self.attack_engine.add_modifier(ImpedanceSpikeAttack([0, 1], spike_value=simulation_context["impedance_kohm"]))
                elif attack_type == "suppression":
                    self.attack_engine.add_modifier(SignalSuppressionAttack([0, 1], attenuation_factor=simulation_context["attenuation_factor"]))
                    
            # Update DBS attacks
            if attack_type == "phase_shift":
                simulation_context["dbs_attack"] = "phase_shift"
            else:
                simulation_context["dbs_attack"] = ""
                
            # If stimulation leak is chosen and secure mode is NOT active, trigger it immediately
            if attack_type == "stimulation_leak":
                if not simulation_context["secure_mode"]:
                    from vireon.plugins.clinical.closed_loop import UncontrolledStimulationAttack
                    leak = UncontrolledStimulationAttack(self.twin)
                    leak.apply()
                else:
                    # If secure mode is active, clamp it safely
                    from vireon.core.security import NeuroSignalAssuranceEngine, NeuroIPS
                    temp_ids = NeuroSignalAssuranceEngine(self.twin)
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
    pass

def start_web_server(twin: DigitalTwin, attack_engine: SignalAttackEngine, port: int = 7777, ips = None, link_guard = None, ws_token: str = "") -> ThreadedHTTPServer:
    # Set request handler globals
    BCIAPIRequestHandler.twin = twin
    BCIAPIRequestHandler.attack_engine = attack_engine
    BCIAPIRequestHandler.ips = ips
    BCIAPIRequestHandler.link_guard = link_guard
    
    simulation_context["ws_token"] = ws_token
    
    # Resolve index.html target directories
    current_dir = os.path.dirname(os.path.abspath(__file__))
    BCIAPIRequestHandler.web_dir = os.path.join(current_dir, "web")
    
    server = ThreadedHTTPServer(("0.0.0.0", port), BCIAPIRequestHandler)
    
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    return server
