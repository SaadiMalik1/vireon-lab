import os
import sys
from typing import Optional, Dict, Any, List
from pathlib import Path

# Add qtara to sys.path so we can import it directly without requiring a system install
qtara_src = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../neurosecurity/datalake/qtara/src'))
if qtara_src not in sys.path:
    sys.path.insert(0, qtara_src)

from qtara.core import TaraLoader

class ThreatIntelligence:
    """
    Threat Intelligence Engine backed by the qTARA framework.
    Loads the neurosecurity/datalake/qtara-registrar.json file to map simulated anomalies
    to real-world documented neural threats and their corresponding NISS scores.
    """
    def __init__(self, registry_path: str):
        self.registry_path = registry_path
        self.loader = TaraLoader(data_path=Path(registry_path))
        try:
            self.loader.load()
            print(f"[ThreatIntel] Loaded {len(self.loader.registry.techniques)} TARA techniques from {registry_path}.")
        except Exception as e:
            print(f"[ThreatIntel] Error loading TARA registry from {registry_path}: {e}")

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
        }
        
        tara_id = mapping.get(attack_name)
        if not tara_id and attack_name != "none":
            tara_id = "QIF-T0001" # Default to signal injection
            
        if not tara_id:
            return None

        tech = self.loader.get_technique(tara_id)
        if tech:
            physics_tier = tech.physics_feasibility.tier_label if tech.physics_feasibility else "Unknown"
            niss_score = tech.niss.score if tech.niss else 0.0
            niss_vector = tech.niss.vector if tech.niss else "N/A"
            dual_use = tech.tara.dual_use if tech.tara else "unknown"
            clinical_analog = tech.tara.clinical.therapeutic_analog if tech.tara and tech.tara.clinical else "None"
            
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
        
        return None
