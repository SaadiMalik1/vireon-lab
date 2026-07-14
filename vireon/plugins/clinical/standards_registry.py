import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger("QIFRegistry")

@dataclass
class QIFThreatTechnique:
    id: str
    name: str
    category: str
    tactic: str
    severity: str
    description: str
    niss_vector: str
    niss_score: float
    bands: List[str]
    dsm5_primary: List[Dict[str, str]]
    dsm5_cluster: str
    physics_tier: int
    physics_gate: str
    dual_use: str

class QIFRegistry:
    _instance = None
    _techniques: Dict[str, QIFThreatTechnique] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QIFRegistry, cls).__new__(cls)
            cls._instance._load_qif()
        return cls._instance

    def _load_qif(self):
        qif_path = os.path.join(os.path.dirname(__file__), "data", "qif.json")
        if not os.path.exists(qif_path):
            logger.warning("qif.json not found offline. Registry will be empty.")
            return

        try:
            with open(qif_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            techniques = data.get("threats", {}).get("techniques", [])
            for tech in techniques:
                t_id = tech.get("id")
                if not t_id:
                    continue
                
                niss_data = tech.get("niss", {})
                dsm5_data = tech.get("dsm5", {})
                physics_data = tech.get("physicsFeasibility", {})
                tara_data = tech.get("tara", {})

                self._techniques[t_id] = QIFThreatTechnique(
                    id=t_id,
                    name=tech.get("name", "Unknown"),
                    category=tech.get("category", "Unknown"),
                    tactic=tech.get("tactic", "Unknown"),
                    severity=tech.get("severity", "low"),
                    description=tech.get("description", ""),
                    niss_vector=niss_data.get("vector", ""),
                    niss_score=niss_data.get("score", 0.0),
                    bands=tech.get("bands", []),
                    dsm5_primary=dsm5_data.get("primary", []),
                    dsm5_cluster=dsm5_data.get("cluster", "Unknown"),
                    physics_tier=physics_data.get("tier", 99),
                    physics_gate=physics_data.get("gate_reason", ""),
                    dual_use=tara_data.get("dual_use", "unknown")
                )
            logger.info(f"Loaded {len(self._techniques)} threat techniques from QIF Atlas.")
        except Exception as e:
            logger.error(f"Error loading qif.json: {e}")

    @classmethod
    def get_technique(cls, technique_id: str) -> Optional[QIFThreatTechnique]:
        registry = cls()
        return registry._techniques.get(technique_id)

    @classmethod
    def get_all_techniques(cls) -> List[QIFThreatTechnique]:
        registry = cls()
        return list(registry._techniques.values())
