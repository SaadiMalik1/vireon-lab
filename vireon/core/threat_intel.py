import os
import json
from typing import Optional, Dict, Any

class ThreatIntelligence:
    """
    Threat Intelligence Engine backed by the VIREON Validation Profile.
    Loads the standards_mapping.json file to map simulated anomalies
    to real-world documented standards (STRIDE, MITRE, CWE, ISO 14971).
    """
    def __init__(self, registry_path: str = None):
        self.registry = {}
        
        # Load the internal standards mapping
        mapping_path = os.path.join(os.path.dirname(__file__), "data", "standards_mapping.json")
        try:
            with open(mapping_path, 'r') as f:
                data = json.load(f)
                self.registry = data.get("techniques", {})
            print(f"[ThreatIntel] Loaded {len(self.registry)} standard threat mappings from VIREON Validation Profile.")
        except Exception as e:
            print(f"[ThreatIntel] Critical: Failed to load standards mapping registry: {e}")

    def resolve_attack(self, attack_name: str) -> Optional[Dict[str, Any]]:
        """
        Maps an internal simulation attack name to established standards.
        Returns a dictionary containing the technique details (STRIDE, MITRE, CWE, ISO).
        """
        if attack_name == "none" or attack_name is None:
            return None
            
        # Try direct match
        tech = self.registry.get(attack_name)
        
        # If no direct match, check if it's a known alias
        if not tech:
            # simple alias resolution if needed
            if "noise" in attack_name:
                tech = self.registry.get("noise_injection")
            elif "drift" in attack_name:
                tech = self.registry.get("drift")
            else:
                return None
                
        if tech:
            return {
                "tara_id": tech.get("cwe", "Unknown"), # Keep key for backwards compatibility, but store CWE
                "name": tech.get("name"),
                "stride": tech.get("stride"),
                "mitre_attack": tech.get("mitre_attack"),
                "iso_14971_category": tech.get("iso_14971_category"),
                "cwe": tech.get("cwe"),
                "description": tech.get("description"),
                "severity": "High" # Default for backwards compatibility if needed
            }
            
        return None
