import logging

logger = logging.getLogger(__name__)

class ThreatAtlas:
    """
    Open Neural Atlas mapping for Threat Modeling.
    Translates physical BCI attacks into psychiatric/neurological outcomes based on disrupted neural pathways.
    (References DSM-5-TR diagnostic categories for threat modeling purposes)
    """

    # Primary DSM-5-TR Diagnostic Clusters mapped to neural pathways
    from typing import Dict, Any
    DSM5_MAPPINGS: Dict[str, Dict[str, Any]] = {
        "N7_PFC_M1": {
            "cluster": "Cognitive/Psychotic",
            "diagnoses": ["F20_SCHIZOPHRENIA_SPECTRUM", "F90_ADHD", "F32_MAJOR_DEPRESSION"],
            "severity_multiplier": 1.2
        },
        "N6_HIPPOCAMPUS_AMYGDALA": {
            "cluster": "Mood/Trauma",
            "diagnoses": ["F32_MAJOR_DEPRESSION", "F41_ANXIETY", "F43_PTSD"],
            "severity_multiplier": 1.5
        },
        "N5_STRIATUM_STN": {
            "cluster": "Motor/Neurocognitive",
            "diagnoses": ["G20_PARKINSONS_EXACERBATION", "F90_ADHD"],
            "severity_multiplier": 1.4
        },
        "N4_THALAMUS": {
            "cluster": "Motor/Neurocognitive",
            "diagnoses": ["F01_VASCULAR_DEMENTIA_MIMICRY", "F20_SCHIZOPHRENIA_SPECTRUM"],
            "severity_multiplier": 1.3
        }
    }

    # Dynamic Attack Techniques from STIX 2.1 Bundle
    ATTACK_TECHNIQUES: dict[str, dict[str, str]] = {}
    _stix_loaded = False

    @classmethod
    def _load_stix_data(cls):
        if cls._stix_loaded:
            return
            
        import os
        import json
        
        stix_path = os.path.join(os.path.dirname(__file__), "data", "tara_stix.json")
        if not os.path.exists(stix_path):
            logger.warning(f"STIX bundle not found at {stix_path}. Falling back to default.")
            cls.ATTACK_TECHNIQUES = {
                "ATLAS-T0009": {"name": "RF false brainwave injection", "pathways": ["N7_PFC_M1", "N6_HIPPOCAMPUS_AMYGDALA"], "base_niss": 7.4},
                "ATLAS-T0011": {"name": "Intermodulation (BCI signal weaponized)", "pathways": ["N6_HIPPOCAMPUS_AMYGDALA", "N5_STRIATUM_STN"], "base_niss": 7.4},
                "ATLAS-T0023": {"name": "Closed-loop perturbation cascade", "pathways": ["N7_PFC_M1", "N6_HIPPOCAMPUS_AMYGDALA"], "base_niss": 7.4},
                "ATLAS-T0030": {"name": "Motor hijacking", "pathways": ["N7_PFC_M1", "N6_HIPPOCAMPUS_AMYGDALA", "N5_STRIATUM_STN"], "base_niss": 6.7},
                "ATLAS-T0068": {"name": "Bifurcation forcing", "pathways": ["N5_STRIATUM_STN", "N4_THALAMUS"], "base_niss": 8.1}
            }
            cls._stix_loaded = True
            return
            
        try:
            with open(stix_path, "r", encoding="utf-8") as f:
                bundle = json.load(f)
                
            for obj in bundle.get("objects", []):
                if obj.get("type") == "attack-pattern":
                    # Extract ID
                    refs = obj.get("external_references", [])
                    ext_id = None
                    for ref in refs:
                        if ref.get("source_name") == "ATLAS TARA" and "external_id" in ref:
                            ext_id = ref["external_id"]
                            break
                    if not ext_id:
                        continue
                        
                    # Extract Severity
                    sev_str = obj.get("x_atlas_severity", "low").lower()
                    if sev_str == "critical":
                        base_niss = 9.0
                    elif sev_str == "high":
                        base_niss = 7.4
                    elif sev_str == "medium":
                        base_niss = 5.0
                    else:
                        base_niss = 3.0
                    
                    # Extract Pathways (Bands)
                    bands = obj.get("x_atlas_bands", [])
                    pathways = []
                    # Map prefix (N7, N6) to full pathway if it exists in DSM5_MAPPINGS
                    # e.g., "N7" matches "N7_PFC_M1"
                    for b in bands:
                        for p_key in cls.DSM5_MAPPINGS.keys():
                            if p_key.startswith(b):
                                pathways.append(p_key)
                                
                    cls.ATTACK_TECHNIQUES[ext_id] = {
                        "name": obj.get("name", "Unknown"),
                        "pathways": list(set(pathways)),
                        "base_niss": base_niss
                    }
                    
            cls._stix_loaded = True
            logger.info(f"Loaded {len(cls.ATTACK_TECHNIQUES)} techniques from STIX bundle.")
        except Exception as e:
            logger.error(f"Failed to parse STIX bundle: {e}")

    @classmethod
    def evaluate_clinical_impact(cls, attack_signature: str, duration_sec: float) -> dict:
        """
        Evaluate the likely psychiatric/clinical outcome of an attack based on the Threat Atlas.
        
        Args:
            attack_signature (str): The specific attack type detected (maps to Atlas techniques)
            duration_sec (float): How long the attack has been active
            
        Returns:
            dict: {
                "dsm5_diagnosis": str,
                "diagnostic_cluster": str,
                "niss_score": float,
                "iso14971_severity": str
            }
        """
        # Map generic simulator attacks to Atlas specific techniques if needed
        technique_id = cls._map_to_atlas_technique(attack_signature)
        
        cls._load_stix_data()
        
        if technique_id not in cls.ATTACK_TECHNIQUES:
            return {
                "dsm5_diagnosis": "UNKNOWN_NEUROLOGICAL_IMPACT",
                "diagnostic_cluster": "Unknown",
                "niss_score": 0.0,
                "iso14971_severity": "MARGINAL"
            }
            
        technique = cls.ATTACK_TECHNIQUES[technique_id]
        
        # Aggregate pathways to find worst outcome
        primary_diagnosis = "UNKNOWN"
        primary_cluster = "UNKNOWN"
        max_multiplier = 1.0
        
        for pathway in technique["pathways"]:
            if pathway in cls.DSM5_MAPPINGS:
                mapping = cls.DSM5_MAPPINGS[pathway]
                multiplier = float(mapping["severity_multiplier"])
                if multiplier >= max_multiplier:
                    max_multiplier = multiplier
                    primary_cluster = str(mapping["cluster"])
                    # Pick the first/most severe diagnosis for the primary pathway
                    primary_diagnosis = str(mapping["diagnoses"][0])

        # Calculate final Neural Impact Severity Score (NISS)
        # NISS increases with duration of exposure (simulating persistent/personality drift)
        duration_factor = min(2.0, 1.0 + (duration_sec / 300.0))  # Caps at 2x after 5 minutes
        niss_score = min(10.0, float(technique["base_niss"]) * max_multiplier * duration_factor)

        # Map NISS to ISO 14971 Severity
        if niss_score >= 8.0:
            iso_severity = "CATASTROPHIC"
        elif niss_score >= 6.0:
            iso_severity = "CRITICAL"
        elif niss_score >= 4.0:
            iso_severity = "MARGINAL"
        else:
            iso_severity = "NEGLIGIBLE"

        return {
            "dsm5_diagnosis": primary_diagnosis,
            "diagnostic_cluster": primary_cluster,
            "niss_score": round(niss_score, 1),
            "iso14971_severity": iso_severity,
            "atlas_technique": technique_id
        }

    @classmethod
    def _map_to_atlas_technique(cls, attack_signature: str) -> str:
        """Maps internal attack names to Threat Atlas T-codes."""
        mapping = {
            "noise_injection": "ATLAS-T0009",      # RF false brainwave
            "phase_shift": "ATLAS-T0023",          # Closed-loop cascade
            "signal_suppression": "ATLAS-T0011",   # Intermodulation
            "firmware_override": "ATLAS-T0068",    # Bifurcation forcing
            "stimulation_leak": "ATLAS-T0030",     # Motor hijacking
        }
        return mapping.get(attack_signature.lower(), "UNKNOWN")
