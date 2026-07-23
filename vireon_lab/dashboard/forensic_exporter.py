# Copyright 2026 VIREON Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from datetime import datetime, timezone

def generate_stix_package(active_attack: str, anomaly_score: float, niss_score: int, clinical_status: str) -> str:
    """
    Generates a STIX 2.1 compliant JSON bundle for forensic neurosecurity evidence.
    """
    now = datetime.now(timezone.utc).isoformat()
    
    stix_bundle = {
        "type": "bundle",
        "id": f"bundle--{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "spec_version": "2.1",
        "objects": [
            {
                "type": "identity",
                "id": "identity--vireon-neurosecurity-lab",
                "created": now,
                "modified": now,
                "name": "VIREON Medical BCI Security Laboratory",
                "identity_class": "system"
            },
            {
                "type": "indicator",
                "id": f"indicator--{hash(active_attack)}",
                "created": now,
                "modified": now,
                "name": f"Neurosecurity Anomaly Alert: {active_attack.upper()}",
                "description": f"Real-time neurosecurity IDS anomaly score: {anomaly_score:.3f}. Clinical Status: {clinical_status}.",
                "indicator_types": ["anomalous-activity"],
                "pattern": f"[neuro-telemetry:anomaly_score > {anomaly_score:.2f}]",
                "pattern_type": "stix",
                "valid_from": now
            },
            {
                "type": "observed-data",
                "id": f"observed-data--{datetime.now().strftime('%S%f')}",
                "created": now,
                "modified": now,
                "first_observed": now,
                "last_observed": now,
                "number_observed": 1,
                "objects": {
                    "0": {
                        "type": "x-vireon-telemetry",
                        "active_attack": active_attack,
                        "niss_score": niss_score,
                        "anomaly_score": anomaly_score,
                        "clinical_status": clinical_status,
                        "iso_14971_risk_level": "CRITICAL" if niss_score > 70 else ("HIGH" if niss_score > 40 else "LOW")
                    }
                }
            }
        ]
    }
    
    return json.dumps(stix_bundle, indent=2)

def generate_html_audit_report(active_attack: str, anomaly_score: float, niss_score: int, clinical_status: str) -> str:
    """
    Generates a standalone HTML executive audit report for clinical compliance.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    risk_level = "CRITICAL" if niss_score > 70 else ("HIGH" if niss_score > 40 else "NOMINAL")
    status_color = "#ff0844" if risk_level == "CRITICAL" else ("#f7b731" if risk_level == "HIGH" else "#2ed573")
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>VIREON Neurosecurity Audit Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 40px; }}
        .header {{ border-bottom: 2px solid #3b82f6; padding-bottom: 20px; margin-bottom: 30px; }}
        .card {{ background-color: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 20px; border: 1px solid #334155; }}
        .badge {{ display: inline-block; padding: 6px 16px; border-radius: 20px; font-weight: bold; background-color: {status_color}; color: #ffffff; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ border: 1px solid #334155; padding: 12px; text-align: left; }}
        th {{ background-color: #0f172a; color: #60a5fa; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 VIREON Executive Forensic Audit Report</h1>
        <p>Generated: {now} | Target: Closed-Loop Implantable Medical Device (IMD)</p>
    </div>
    <div class="card">
        <h2>Clinical Risk & Vulnerability Summary</h2>
        <p>Overall Security Health Index: <span class="badge">{risk_level}</span></p>
        <table>
            <tr><th>Metric</th><th>Observed Value</th><th>Regulatory Target</th></tr>
            <tr><td>Active Threat Vector</td><td><strong>{active_attack.upper()}</strong></td><td>NONE</td></tr>
            <tr><td>Neurosecurity Anomaly Score</td><td>{anomaly_score:.4f}</td><td>&lt; 0.3500</td></tr>
            <tr><td>NISS (Neuro Severity Score)</td><td>{niss_score} / 100</td><td>0</td></tr>
            <tr><td>Clinical State Machine</td><td>{clinical_status}</td><td>Nominal (Therapeutic)</td></tr>
        </table>
    </div>
    <div class="card">
        <h2>ISO 14971 Risk Controls & Mitigations</h2>
        <p>1. Hardware Bridge: Pulse amplitude current limiter engaged.</p>
        <p>2. Cryptographic Attestation: Telemetry Session Token verification active.</p>
        <p>3. Dynamic IDS: Automated fallback to Safe Mode on anomalous signal detection.</p>
    </div>
</body>
</html>"""
    return html
