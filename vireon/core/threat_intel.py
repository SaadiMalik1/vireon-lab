import os
import sys
import json
from typing import Optional, Dict, Any, List
from pathlib import Path

# Add qtara to sys.path so we can import it directly without requiring a system install
qtara_src = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../neurosecurity/datalake/qtara/src'))
if qtara_src not in sys.path:
    sys.path.insert(0, qtara_src)

try:
    from qtara.core import TaraLoader
    QTARA_AVAILABLE = True
except ImportError:
    QTARA_AVAILABLE = False
    print("[ThreatIntel] Warning: qtara module not found. Falling back to local stub registry.")

class ThreatIntelligence:
    """
    Threat Intelligence Engine backed by the qTARA framework.
    Loads the neurosecurity/datalake/qtara-registrar.json file to map simulated anomalies
    to real-world documented neural threats and their corresponding NISS scores.
    """
    def __init__(self, registry_path: str):
        self.registry_path = registry_path
        self.loader = None
        self.fallback_registry = {}
        
        if QTARA_AVAILABLE and os.path.exists(registry_path):
            self.loader = TaraLoader(data_path=Path(registry_path))
            try:
                self.loader.load()
                print(f"[ThreatIntel] Loaded {len(self.loader.registry.techniques)} TARA techniques from {registry_path}.")
            except Exception as e:
                print(f"[ThreatIntel] Error loading TARA registry from {registry_path}: {e}. Using fallback.")
                self._load_fallback()
        else:
            self._load_fallback()

    def _load_fallback(self):
        fallback_path = os.path.join(os.path.dirname(__file__), "data", "qtara_stub.json")
        try:
            with open(fallback_path, 'r') as f:
                data = json.load(f)
                for tech in data.get("techniques", []):
                    self.fallback_registry[tech["id"]] = tech
            print(f"[ThreatIntel] Loaded {len(self.fallback_registry)} fallback TARA techniques from {fallback_path}.")
        except Exception as e:
            print(f"[ThreatIntel] Critical: Failed to load fallback registry: {e}")

    def resolve_attack(self, attack_name: str) -> Optional[Dict[str, Any]]:
        """
        Maps an internal simulation attack name to a TARA technique using qTARA.
        Returns a dictionary containing the technique details, NISS score, and physics feasibility.
        """
        # Mapping simulation attack types to TARA IDs
        mapping = {
            "noise": "QIF-T0001",           # Signal injection
            "drift": "QIF-T0040",           # Drift attack
            "impedance": "QIF-T0025",       # Neuronal jamming
            "suppression": "QIF-T0029",     # Neural DoS
            "stimulation_leak": "QIF-T0002", # Neural ransomware
            "pairing_fail": "QIF-T0088",    # BLE pairing disruption
            "mtu_abuse": "QIF-T0089",       # Protocol MTU abuse
            "temporal_evasion": "QIF-T0045",# High-frequency bursting
            "session_replay": "QIF-T0050",  # Replay masking attack
        }
        
        tara_id = mapping.get(attack_name)
        if not tara_id and attack_name != "none":
            tara_id = "QIF-T0001" # Default to signal injection
            
        if not tara_id:
            return None

        if self.loader and hasattr(self.loader, "get_technique"):
            tech = self.loader.get_technique(tara_id)
            if tech:
                physics_tier = tech.physics_feasibility.tier_label if hasattr(tech, "physics_feasibility") and tech.physics_feasibility else "Unknown"
                niss_score = tech.niss.score if hasattr(tech, "niss") and tech.niss else 0.0
                niss_vector = tech.niss.vector if hasattr(tech, "niss") and tech.niss else "N/A"
                dual_use = tech.tara.dual_use if hasattr(tech, "tara") and tech.tara else "unknown"
                clinical_analog = tech.tara.clinical.therapeutic_analog if hasattr(tech, "tara") and tech.tara and hasattr(tech.tara, "clinical") and tech.tara.clinical else "None"
                
                return {
                    "tara_id": tech.id,
                    "name": tech.attack,
                    "severity": tech.severity,
                    "niss_vector": niss_vector,
                    "niss_score": niss_score,
                    "physics_tier": physics_tier,
                    "description": tech.notes or tech.attack,
                    "dual_use": dual_use,
                    "clinical_analog": clinical_analog
                }
        else:
            # Use fallback registry
            if tara_id in self.fallback_registry:
                tech = self.fallback_registry[tara_id]
                return {
                    "tara_id": tech["id"],
                    "name": tech["name"],
                    "severity": tech["severity"],
                    "niss_vector": "N/A",
                    "niss_score": 5.0,
                    "physics_tier": "Unknown",
                    "description": tech["description"],
                    "dual_use": "unknown",
                    "clinical_analog": "None"
                }
        
        return None
