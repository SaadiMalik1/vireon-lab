"""
WARNING: This module is for simulation purposes only.
The MCP Server trust boundary is undefined. It runs with no persistence and no real 
trust establishment protocol. Do not deploy this in a production network.
"""
from mcp.server.fastmcp import FastMCP
from typing import List, Optional
import json
import hashlib
import hmac
import base64
import os
import secrets

from vireon.core.coordinator import Coordinator
from vireon.core.plugin_registry import PluginRegistry, register_builtin_plugins

# Create the MCP server instance
mcp = FastMCP("VIREON-Neural-Terminal")

# -----------------------------------------------------------------------------
# NEURO_DSL CAPABILITY SYSTEM (Simulated)
# -----------------------------------------------------------------------------
# In the NeuroDSL architecture, access is governed by cryptographically 
# verifiable capability tokens mapped to Neurorights.

SECRET_FILE = os.path.expanduser("~/.vireon/mcp_secret.key")
if os.path.exists(SECRET_FILE):
    with open(SECRET_FILE, "rb") as f_in:
        SERVER_SECRET = f_in.read()
else:
    os.makedirs(os.path.dirname(SECRET_FILE), exist_ok=True)
    SERVER_SECRET = secrets.token_bytes(32)
    with open(SECRET_FILE, "wb") as f_out:
        f_out.write(SERVER_SECRET)

def _verify_capability(session_token: str, required_capability: str) -> bool:
    try:
        raw = base64.b64decode(session_token)
        if b"|" not in raw:
            return False
        payload_bytes, sig = raw.rsplit(b"|", 1)
        expected_sig = hmac.new(SERVER_SECRET, payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected_sig):
            return False
        payload = json.loads(payload_bytes.decode())
        caps = payload.get("c", [])
        return required_capability in caps
    except Exception:
        return False

@mcp.tool()
def mock_authenticate_session(biomarker_hash: str, role: str = "patient", auth_signature: Optional[str] = None) -> str:
    """
    WARNING: This is a MOCK authentication function. It does not perform real
    Advanced Cryptography (PQKC) or actual biomarker validation. It is solely
    for simulating the authentication flow in the digital twin environment.
    
    Simulates Advanced Key Exchange and Biomarker MFA authentication.
    
    Args:
        biomarker_hash: A simulated hash of the user's EEG/P300 signature.
        role: "patient" or "clinician" to determine capability scope.
        auth_signature: Cryptographic signature required for clinician role escalation.
        
    Returns:
        JSON string containing the session token and granted capabilities.
    """
    # Enforce cryptographic signature for clinician role escalation
    if role == "clinician":
        # In a real system, this would be a proper PKI or asymmetric signature verification.
        # For the simulation, we use an environment variable to simulate the PKI validation 
        # without hardcoding symmetric secrets.
        expected_sig = os.environ.get("CLINICIAN_PUB_KEY")
        if not expected_sig:
            return json.dumps({"error": "Role Escalation Denied: Server misconfiguration (CLINICIAN_PUB_KEY missing)."})
            
        if not auth_signature or auth_signature != expected_sig:
            return json.dumps({"error": "Role Escalation Denied: Invalid or missing cryptographic signature for clinician."})

    # Map roles to Neuroright-based capabilities
    if role == "patient":
        capabilities = [
            "perceive.visual", "perceive.auditory", "perceive.haptic",
            "config.contrast", "config.refresh", "log.read"
        ]
    elif role == "clinician":
        capabilities = [
            "calibrate.electrodes", "calibrate.thresholds",
            "log.read", "log.export", "device.diagnostics", "simulation.run"
        ]
    else:
        return json.dumps({"error": f"Unknown role: {role}"})
        
    # Simulate a PQKC key exchange generating a secure session token
    # using a stateless JWT-like signed token system with HMAC
    payload = json.dumps({"b": biomarker_hash, "r": role, "c": capabilities})
    sig = hmac.new(SERVER_SECRET, payload.encode(), hashlib.sha256).digest()
    session_token = base64.b64encode(payload.encode() + b"|" + sig).decode()
    
    return json.dumps({
        "status": "Authentication Successful",
        "session_token": session_token,
        "role": role,
        "granted_capabilities": capabilities,
        "message": "Store this session_token. It is required for restricted tools."
    }, indent=2)


def _get_registry():
    registry = PluginRegistry()
    register_builtin_plugins(registry)
    return registry

@mcp.tool()
def get_available_plugins() -> str:
    """
    List all available plugins in the VIREON Reference Platform.
    Requires NO authentication (public metadata).
    """
    registry = _get_registry()
    cats = registry.list_categories()
    
    result: dict[str, dict[str, list[dict[str, str]]]] = {"categories": {}}
    for cat in cats:
        plugins = registry.list_category(cat)
        result["categories"][cat] = [
            {"name": info.name, "description": info.description} 
            for info in plugins
        ]
        
    return json.dumps(result, indent=2)

@mcp.tool()
def run_simulation(
    session_token: str,
    duration_sec: float = 5.0,
    attacks: Optional[List[str]] = None,
    secure_mode: bool = True,
    device: str = "synthetic",
    dbs_mode: bool = False,
    dbs_attack: Optional[str] = None
) -> str:
    """
    Run a VIREON simulation in headless mode. 
    REQUIRES authentication with the 'simulation.run' capability.
    
    Args:
        session_token: A valid token generated via mock_authenticate_session.
        duration_sec: How long to run the simulation in seconds.
        attacks: List of signal/firmware attacks.
        secure_mode: Whether the IDS/IPS security shield is active.
        device: The hardware board emulator to use.
        dbs_mode: Enable the Deep Brain Stimulation closed-loop model.
        dbs_attack: Inject a DBS-specific attack.
    """
    # Capability Check (NeuroDSL Tier 3-4 Enforcement)
    if not _verify_capability(session_token, "simulation.run"):
        return json.dumps({
            "error": "Permission Denied: Capability 'simulation.run' required.",
            "enforcement_layer": "Neurowall Capability Gate"
        }, indent=2)

    # Build raw config dictionary equivalent to what the CLI would generate
    raw_config = {
        "experiment": {
            "name": "mcp_sim",
            "duration_sec": duration_sec
        },
        "device": {
            "type": device,
            "sample_rate": 250
        },
        "attacks": {
            "active": attacks or [],
            "noise_level_uv": 80.0,
            "drift_slope_uv_s": 25.0
        },
        "security": {
            "enabled": secure_mode,
            "nsp_enabled": True # Enforce advanced wrapper
        },
        "emulation": {
            "dbs_mode": dbs_mode,
            "dbs_attack": dbs_attack if dbs_attack is not None else ""
        }
    }

    # Initialize coordinator with the raw config
    from vireon.core.config import ExperimentConfig
    config = ExperimentConfig.model_validate(raw_config)
    coordinator = Coordinator(config)
    coordinator.setup()
    
    # Run the simulation (blocks for duration_sec)
    coordinator.run()
    
    # Capture the final state of the digital twin
    final_state = coordinator.twin.get_state() if coordinator.twin else {}
    coordinator.teardown()
    
    # Return key safety metrics
    return json.dumps({
        "status": "Simulation Complete",
        "session_verified": True,
        "duration_sec": duration_sec,
        "secure_mode": secure_mode,
        "attacks_injected": attacks or [],
        "dbs_attack_injected": dbs_attack,
        "final_hazard_state": final_state.get("hazard_state", "UNKNOWN"),
        "final_clinical_status": final_state.get("clinical_status", "UNKNOWN"),
        "tissue_damage_risk_pct": final_state.get("tissue_damage_risk", 0.0)
    }, indent=2)

if __name__ == "__main__":
    # Start the stdio MCP server
    mcp.run(transport="stdio")
