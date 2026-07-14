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

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


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
    qtara_id: Optional[str] = None
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
    severity_counts = {}
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
    """Enumerate all known threats across VIREON's attack surface."""
    threats = []
    tid = 0

    def _t(cat, component, asset, desc, vector, sev, like, mitigation, module, qtara=None):
        nonlocal tid
        tid += 1
        threats.append(ThreatEntry(
            stride_category=cat,
            threat_id=f"NS-{cat}-{tid:03d}",
            component=component,
            asset=asset,
            threat_description=desc,
            attack_vector=vector,
            severity=sev,
            likelihood=like,
            existing_mitigation=mitigation,
            mitigation_module=module,
            qtara_id=qtara,
        ))

    # ==================== SPOOFING ====================
    _t("S", "BLE Transport", "Device Identity",
       "Attacker spoofs a BCI device by cloning its BLE advertisement and MAC address",
       "Proximity-based BLE spoofing with cloned advertising data",
       "High", "Medium",
       "BLE Link Guard pairing state machine validates bonding sequence",
       "vireon.core.security.BLELinkGuard")

    _t("S", "RF Telemetry", "Frame Origin",
       "Attacker injects forged telemetry frames with valid preamble",
       "RF replay or injection using SDR (Software Defined Radio)",
       "High", "Medium",
       "HMAC-SHA256 frame authentication in secure mode; sequence number validation",
       "vireon.core.protocol.RFFrameProcessor",
       "QIF-T2202")

    _t("S", "Closed-Loop Controller", "Decoder Input",
       "Adversarial signal injection causes decoder to misclassify brain state",
       "Signal-level adversarial perturbation targeting ML decoder",
       "Critical", "Medium",
       "Bandpass defense filter + autoencoder structural deviation detection",
       "vireon.core.ml_decoder.AdversarialDefenseFilter",
       "QIF-T2202")

    _t("S", "Session Replay", "Signal Authenticity",
       "Attacker captures clean EEG segment and replays it to mask real activity",
       "SessionReplayAttack: capture clean data, then loop over target channels",
       "High", "Medium",
       "Spectral entropy analysis detects statistical uniformity of replayed signals",
       "vireon.core.security.NeuroSignalAssuranceEngine")

    # ==================== TAMPERING ====================
    _t("T", "RF Telemetry", "Frame Payload",
       "Attacker modifies telemetry frame payload in transit (bit-flip, data injection)",
       "Man-in-the-middle modification of raw RF frames",
       "Critical", "Medium",
       "AES-GCM authenticated encryption with 128-bit auth tag; CRC-16 for plaintext mode",
       "vireon.core.protocol.CryptoEmulator",
       "QIF-T2102")

    _t("T", "Stimulation Parameters", "DBS Amplitude/Frequency",
       "Attacker modifies stimulation commands to induce tissue damage",
       "Command injection via compromised programmer or wireless intercept",
       "Critical", "High",
       "IPS hard-clamps amplitude (4.0mA), cumulative charge (5200μC), and thermal dose",
       "vireon.core.security.NeuroIPS",
       "QIF-T2301")

    _t("T", "Digital Twin State", "Clinical Variables",
       "Attacker manipulates twin state to suppress safety alerts",
       "Direct memory manipulation or race condition on shared state",
       "High", "Low",
       "Thread-locked state access (hardware_lock, clinical_lock, therapy_lock)",
       "vireon.core.twin.DigitalTwin")

    _t("T", "Cyton Framing", "Parser State",
       "Attacker injects ADC values that encode as framing bytes (0xA0/0xC0)",
       "FramingDesynchronizationAttack: crafted microvolt values exploit unescaped framing",
       "Medium", "Medium",
       "IDS detects spectral anomalies from constant-value injection",
       "vireon.core.security.NeuroSignalAssuranceEngine")

    # ==================== REPUDIATION ====================
    _t("R", "Event Bus", "Attack Timeline",
       "Attacker performs signal manipulation but no audit trail exists",
       "Attacks executed without logging or non-repudiation evidence",
       "Medium", "Medium",
       "EventBus publishes all attack events; IDS logs detections with timestamps and TARA IDs",
       "vireon.core.event_bus.EventBus")

    _t("R", "Stimulation History", "Clinical Actions",
       "Stimulation parameter changes are not cryptographically signed",
       "Modification of stim_history entries after the fact",
       "Medium", "Low",
       "IPS maintains stim_history list with timestamps; report generator includes full timeline",
       "vireon.core.security.NeuroIPS")

    # ==================== INFORMATION DISCLOSURE ====================
    _t("I", "WebSocket Server", "Neural Telemetry",
       "Raw EEG/LFP data streamed over unencrypted WebSocket connection",
       "Network eavesdropping on ws:// connection (not wss://)",
       "High", "High",
       "No encryption on WebSocket transport (GAP — use wss:// or application-level encryption)",
       "vireon.dashboard")

    _t("I", "LSL Stream", "Neural Data",
       "Lab Streaming Layer broadcasts neural data on local network without access control",
       "Any device on the LAN can subscribe to LSL streams",
       "Medium", "High",
       "LSL is designed for lab environments; no built-in access control (KNOWN LIMITATION)",
       "vireon.core.lsl_streamer")

    _t("I", "Dataset Export", "Patient EEG Files",
       "Exported EDF/CSV files contain biometrically identifiable neural signatures",
       "File exfiltration from shared storage or insecure export path",
       "High", "Medium",
       "No anonymization on exported data (GAP — planned: differential privacy + anonymizer)",
       "vireon.plugins.datasets")

    # ==================== DENIAL OF SERVICE ====================
    _t("D", "RF Telemetry", "Frame Processing",
       "Attacker floods receiver with malformed frames causing exponential backoff sleep",
       "RFJammingAttack: high packet drop rate; telemetry flooding protection activates",
       "High", "High",
       "Exponential backoff duty cycling (5s → 10s → 20s → 60s max) after 3 consecutive failures",
       "vireon.core.protocol.RFFrameProcessor")

    _t("D", "Signal Pipeline", "IDS Processing",
       "Adversarial noise injection saturates IDS with false positives (alert fatigue)",
       "NoiseInjectionAttack at high amplitude across all channels",
       "Medium", "High",
       "CUSUM alarm resets prevent infinite alert loops; IDS detection list capped at 1000 entries",
       "vireon.core.security.NeuroSignalAssuranceEngine",
       "QIF-T2102")

    _t("D", "Digital Twin", "Battery/Temperature",
       "Attacker drives device parameters to failure state (battery drain, thermal shutdown)",
       "Sustained high-amplitude stimulation commands",
       "Medium", "Medium",
       "PhysicsEngine models battery drain and thermal accumulation; IPS enforces thermal limits",
       "vireon.core.physics.PhysicsEngine")

    # ==================== ELEVATION OF PRIVILEGE ====================
    _t("E", "Plugin Registry", "Code Execution",
       "Malicious external plugin loaded via entry_points gains full system access",
       "Supply chain attack: attacker publishes PyPI package with vireon.plugins entry point",
       "Critical", "Low",
       "Plugin whitelist: only vireon.plugins.* namespace allowed; opt-in via plugins.json",
       "vireon.core.plugin_registry.PluginRegistry")

    _t("E", "Stimulation Control", "Safety Limits",
       "Attacker bypasses IPS clamping to set stimulation above safe limits",
       "Direct API call to twin.set_stimulation() bypassing IPS sanitize_stimulation_write()",
       "Critical", "Low",
       "IPS is advisory — direct twin access is possible (architectural limitation)",
       "vireon.core.security.NeuroIPS")

    _t("E", "MCP Server", "Remote Control",
       "Unauthorized MCP client sends control commands to running simulation",
       "MCP server listens without authentication; any local client can connect",
       "High", "Medium",
       "MCP server binds to localhost by default; no authentication (GAP for network deployment)",
       "vireon.mcp_server")

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
            if t.get("qtara_id"):
                lines.append(f"- **qTARA ID:** {t['qtara_id']}")
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
    print("=" * 60)
    print(" VIREON STRIDE Threat Model")
    print("=" * 60)
    print(f"  Generated:     {model['generated_at']}")
    print(f"  Total Threats:  {summary['total_threats']}")
    print()

    print("  By Category:")
    for cat, desc in STRIDE_CATEGORIES.items():
        count = summary["by_category"].get(cat, 0)
        label = desc.split("—")[0].strip()
        print(f"    [{cat}] {label:30s} {count}")
    print()

    print("  By Severity:")
    for sev in ["Critical", "High", "Medium", "Low"]:
        count = summary["by_severity"].get(sev, 0)
        bar = "█" * count
        print(f"    {sev:10s} {count:2d} {bar}")
    print()

    # Highlight gaps
    gaps = []
    for cat_data in model["categories"].values():
        for t in cat_data["threats"]:
            if "GAP" in t.get("existing_mitigation", ""):
                gaps.append(t)

    if gaps:
        print(f"  ⚠ GAPS IDENTIFIED: {len(gaps)}")
        for g in gaps:
            print(f"    {g['threat_id']}: {g['threat_description'][:60]}...")
        print()

    print("=" * 60)
