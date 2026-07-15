import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

"""
VIREON STRIDE Threat Model Auto-Generator.

Introspects the active VIREON configuration and produces a structured
STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, DoS,
Elevation of Privilege) threat model.

Output is both Markdown (human-readable) and JSON (machine-readable),
with cross-references to existing qTARA technique IDs.

References:
  - Microsoft STRIDE Threat Modeling
  - FDA "Cybersecurity in Medical Devices" (Feb 2026) §3.8
  - ISO 14971 Risk Management
"""
@dataclass
class ThreatEntry:
    """A single STRIDE threat entry."""
    stride_category: str       # S, T, R, I, D, E
    threat_id: str
    component: str
    asset: str
    threat_description: str
    attack_vector: str
    severity: str              # Critical, High, Medium, Low
    likelihood: str            # High, Medium, Low
    existing_mitigation: str
    mitigation_module: str
    cptara_id: Optional[str] = None
    residual_risk: str = "Acceptable"


# STRIDE category definitions
STRIDE_CATEGORIES = {
    "S": "Spoofing — Can an attacker assume the identity of another entity?",
    "T": "Tampering — Can an attacker modify data in transit or at rest?",
    "R": "Repudiation — Can an actor deny performing an action?",
    "I": "Information Disclosure — Can sensitive data be exposed?",
    "D": "Denial of Service — Can an attacker disrupt system availability?",
    "E": "Elevation of Privilege — Can an attacker gain unauthorized access?",
}


def generate_stride_model(config: Any = None) -> Dict[str, Any]:
    """
    Generate a STRIDE threat model based on VIREON's architecture.

    Args:
        config: Optional ExperimentConfig. If None, generates a generic model.

    Returns:
        STRIDE threat model dictionary.
    """
    threats = _enumerate_threats(config)

    # Group by category
    by_category: Dict[str, List[Dict]] = {cat: [] for cat in STRIDE_CATEGORIES}
    for t in threats:
        by_category[t.stride_category].append(t.__dict__)

    # Risk summary
    severity_counts: dict[str, int] = {}
    for t in threats:
        severity_counts[t.severity] = severity_counts.get(t.severity, 0) + 1

    model = {
        "model_type": "STRIDE",
        "model_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system": {
            "name": "VIREON Virtual Neurosecurity Laboratory",
            "description": "Simulated BCI/DBS/VNS platform for security research",
            "boundaries": [
                "Signal acquisition (EEG/LFP sensors → ADC → Digital Twin)",
                "Wireless transport (BLE GATT / RF telemetry frames)",
                "Processing pipeline (IDS/IPS → Decoder → Closed-loop controller)",
                "External interfaces (WebSocket, LSL, MCP server, CLI)",
                "Storage (Dataset manager, Report generator)",
            ],
        },
        "categories": {
            cat: {
                "definition": desc,
                "threats": by_category[cat],
                "count": len(by_category[cat]),
            }
            for cat, desc in STRIDE_CATEGORIES.items()
        },
        "summary": {
            "total_threats": len(threats),
            "by_severity": severity_counts,
            "by_category": {cat: len(by_category[cat]) for cat in STRIDE_CATEGORIES},
        },
    }

    return model


def _enumerate_threats(config: Any = None) -> List[ThreatEntry]:
    """Enumerate all known threats across VIREON's attack surface from config."""
    threats = []
    
    config_path = os.path.join(os.path.dirname(__file__), "data", "stride_threats.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            threat_data = json.load(f)
            
        tid = 1
        for t in threat_data:
            threats.append(ThreatEntry(
                stride_category=t["cat"],
                threat_id=f"NS-{t['cat']}-{tid:03d}",
                component=t["component"],
                asset=t["asset"],
                threat_description=t["desc"],
                attack_vector=t["vector"],
                severity=t["sev"],
                likelihood=t["like"],
                existing_mitigation=t["mitigation"],
                mitigation_module=t["module"],
                cptara_id=t.get("cptara")
            ))
            tid += 1
    except Exception as e:
        logger.info(f"Error loading stride threats from config: {e}")
        
    return threats



def render_stride_markdown(model: Dict[str, Any]) -> str:
    """Render STRIDE model as Markdown for documentation."""
    lines = []
    lines.append("# VIREON STRIDE Threat Model")
    lines.append("")
    lines.append(f"Generated: {model['generated_at']}")
    lines.append("")
    lines.append("## System Boundaries")
    for boundary in model["system"]["boundaries"]:
        lines.append(f"- {boundary}")
    lines.append("")

    summary = model["summary"]
    lines.append(f"## Summary: {summary['total_threats']} Threats Identified")
    lines.append("")
    lines.append("| Category | Count | Description |")
    lines.append("|----------|-------|-------------|")
    for cat, desc in STRIDE_CATEGORIES.items():
        count = summary["by_category"].get(cat, 0)
        label = desc.split("—")[0].strip()
        lines.append(f"| **{cat}** — {label} | {count} | {desc.split('—')[1].strip()} |")
    lines.append("")

    lines.append("| Severity | Count |")
    lines.append("|----------|-------|")
    for sev in ["Critical", "High", "Medium", "Low"]:
        count = summary["by_severity"].get(sev, 0)
        lines.append(f"| {sev} | {count} |")
    lines.append("")

    for cat, cat_data in model["categories"].items():
        if not cat_data["threats"]:
            continue
        lines.append(f"## {cat} — {STRIDE_CATEGORIES[cat].split('—')[0].strip()}")
        lines.append("")
        for t in cat_data["threats"]:
            lines.append(f"### {t['threat_id']}: {t['threat_description']}")
            lines.append("")
            lines.append(f"- **Component:** {t['component']}")
            lines.append(f"- **Asset:** {t['asset']}")
            lines.append(f"- **Attack Vector:** {t['attack_vector']}")
            lines.append(f"- **Severity:** {t['severity']} | **Likelihood:** {t['likelihood']}")
            if t.get("cptara_id"):
                lines.append(f"- **qTARA ID:** {t['cptara_id']}")
            lines.append(f"- **Mitigation:** {t['existing_mitigation']}")
            lines.append(f"- **Module:** `{t['mitigation_module']}`")
            lines.append(f"- **Residual Risk:** {t['residual_risk']}")
            lines.append("")

    return "\n".join(lines)


def save_stride_model(model: Dict[str, Any], output_path: str) -> None:
    """Save STRIDE model to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2, ensure_ascii=False)


def print_stride_summary(model: Dict[str, Any]) -> None:
    """Print concise STRIDE summary to console."""
    summary = model["summary"]
    logger.info("=" * 60)
    logger.info(" VIREON STRIDE Threat Model")
    logger.info("=" * 60)
    logger.info(f"  Generated:     {model['generated_at']}")
    logger.info(f"  Total Threats:  {summary['total_threats']}")
    logger.info("")

    logger.info("  By Category:")
    for cat, desc in STRIDE_CATEGORIES.items():
        count = summary["by_category"].get(cat, 0)
        label = desc.split("—")[0].strip()
        logger.info(f"    [{cat}] {label:30s} {count}")
    logger.info("")

    logger.info("  By Severity:")
    for sev in ["Critical", "High", "Medium", "Low"]:
        count = summary["by_severity"].get(sev, 0)
        bar = "█" * count
        logger.info(f"    {sev:10s} {count:2d} {bar}")
    logger.info("")

    # Highlight gaps
    gaps = []
    for cat_data in model["categories"].values():
        for t in cat_data["threats"]:
            if "GAP" in t.get("existing_mitigation", ""):
                gaps.append(t)

    if gaps:
        logger.info(f"  ⚠ GAPS IDENTIFIED: {len(gaps)}")
        for g in gaps:
            logger.info(f"    {g['threat_id']}: {g['threat_description'][:60]}...")
        logger.info("")

    logger.info("=" * 60)
