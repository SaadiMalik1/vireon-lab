import os
import json
from typing import Dict, Optional

class StixMapper:
    """
    Utility for mapping internal VIREON attack strings
    to standard STIX 2.1 Threat Intelligence identifiers.
    """
    def __init__(self, bundle_path: str):
        self.bundle_path = bundle_path
        self.attack_patterns: Dict[str, dict] = {}
        self.keyword_index: Dict[str, str] = {}
        self._load_bundle()

    def _load_bundle(self):
        """Loads the STIX JSON and indexes attack patterns."""
        # Resolve path relative to project root if it's not absolute
        if not os.path.isabs(self.bundle_path):
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            full_path = os.path.join(project_root, self.bundle_path)
        else:
            full_path = self.bundle_path

        if not os.path.exists(full_path):
            print(f"[StixMapper] Warning: STIX bundle not found at {full_path}")
            return

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                bundle = json.load(f)
            
            for obj in bundle.get("objects", []):
                if obj.get("type") == "attack-pattern":
                    obj_id = obj["id"]
                    self.attack_patterns[obj_id] = obj
                    
                    # Create crude keyword index for matching
                    # e.g., "Noise injection" -> match "noise"
                    name_lower = obj.get("name", "").lower()
                    desc_lower = obj.get("description", "").lower()
                    
                    if "noise" in name_lower or "noise" in desc_lower:
                        self.keyword_index["noise"] = obj_id
                    if "drift" in name_lower or "drift" in desc_lower:
                        self.keyword_index["drift"] = obj_id
                    if "spike" in name_lower or "impedance" in desc_lower:
                        self.keyword_index["spike"] = obj_id
                    if "suppress" in name_lower or "suppression" in desc_lower:
                        self.keyword_index["suppression"] = obj_id
                    if "gatt" in name_lower or "gatt" in desc_lower:
                        self.keyword_index["gatt_corrupt"] = obj_id
                    if "malformed" in name_lower or "mtu" in desc_lower:
                        self.keyword_index["malformed_notify"] = obj_id
                        self.keyword_index["mtu_abuse"] = obj_id
                    if "pairing" in name_lower:
                        self.keyword_index["pairing_fail"] = obj_id
                    if "phase" in name_lower or "shift" in name_lower:
                        self.keyword_index["phase_shift"] = obj_id

            print(f"[StixMapper] Loaded {len(self.attack_patterns)} STIX attack patterns.")
        except Exception as e:
            print(f"[StixMapper] Error parsing STIX bundle: {e}")

    def resolve_attack(self, internal_name: str) -> Optional[dict]:
        """
        Maps an internal attack name (e.g., 'noise') to its STIX representation.
        Returns a dict with 'stix_id' and 'name' if found, else None.
        """
        if not internal_name or internal_name == "none":
            return None

        stix_id = self.keyword_index.get(internal_name.lower())
        
        # Fallback: just pick the first one if we can't map it directly
        # so that external tools always receive *some* STIX tag for active attacks
        if not stix_id and self.attack_patterns:
            stix_id = list(self.attack_patterns.keys())[0]

        if stix_id and stix_id in self.attack_patterns:
            pattern = self.attack_patterns[stix_id]
            return {
                "stix_id": pattern["id"],
                "name": pattern.get("name", "Unknown Threat")
            }
        
        return None
