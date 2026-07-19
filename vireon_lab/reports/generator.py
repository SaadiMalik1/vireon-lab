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
import time
from typing import Dict, Any, List
from jinja2 import Environment, BaseLoader, select_autoescape
from markupsafe import Markup
from vireon.runtime.twin import DigitalTwin

# Premium Glassmorphic HTML Template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VIREON Software Audit & Clinical Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Grotesk:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --panel-bg: rgba(17, 25, 40, 0.75);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --accent-cyan: #06b6d4;
            --accent-purple: #a855f7;
            --accent-red: #ef4444;
            --accent-green: #10b981;
            --accent-yellow: #f59e0b;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: 'Outfit', sans-serif;
            min-height: 100vh;
            padding: 2rem;
            line-height: 1.6;
        }

        .container {
            max-width: 1100px;
            margin: 0 auto;
        }

        header {
            background: linear-gradient(135deg, var(--panel-bg), rgba(20, 10, 40, 0.4));
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 24px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        .title-area h1 {
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 800;
            font-size: 2.2rem;
            background: linear-gradient(to right, var(--accent-cyan), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }

        .subtitle {
            color: var(--text-secondary);
            font-size: 1rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }

        .meta-badge {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-color);
            padding: 0.75rem 1.25rem;
            border-radius: 16px;
            font-size: 0.9rem;
            text-align: right;
            color: var(--text-secondary);
        }

        .meta-badge span {
            color: var(--accent-cyan);
            font-weight: 600;
        }

        .grid-3 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .card {
            background: var(--panel-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 1.8rem;
            box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.15);
            position: relative;
            overflow: hidden;
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: linear-gradient(to bottom, var(--accent-cyan), var(--accent-purple));
        }

        .card.alert-active::before {
            background: var(--accent-red);
        }

        .card-title {
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            color: var(--text-secondary);
            margin-bottom: 0.8rem;
        }

        .card-value {
            font-size: 2rem;
            font-weight: 800;
            font-family: 'Space Grotesk', sans-serif;
        }

        .card-desc {
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 0.5rem;
        }

        .chart-section {
            background: var(--panel-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 24px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        }

        .chart-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.25rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .chart-title::before {
            content: '';
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--accent-cyan);
        }

        .svg-chart {
            width: 100%;
            height: auto;
            display: block;
        }

        .table-section {
            background: var(--panel-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 24px;
            padding: 2rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        }

        .table-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.25rem;
            margin-bottom: 1.5rem;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }

        th {
            padding: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--text-secondary);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        td {
            padding: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 0.95rem;
        }

        tr:last-child td {
            border-bottom: none;
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .badge-nominal {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .badge-alert {
            background: rgba(239, 68, 68, 0.15);
            color: var(--accent-red);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .badge-warning {
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-yellow);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="title-area">
                <h1>VIREON Virtual Lab</h1>
                <div class="subtitle">System Security & Clinical Integrity Report</div>
            </div>
            <div class="meta-badge">
                Generated: <span>{{ date_str }}</span><br>
                Device ID: <span>{{ summary.device_id }}</span>
            </div>
        </header>

        <div class="grid-3">
            <div class="card {% if summary.alert_active %}alert-active{% endif %}">
                <div class="card-title">Clinical Status</div>
                <div class="card-value" style="color: {% if summary.current_status == 'Nominal' %}var(--accent-green){% else %}var(--accent-red){% endif %};">
                    {{ summary.current_status }}
                </div>
                <div class="card-desc">Current alert state of the clinical stimulation system</div>
            </div>

            <div class="card">
                <div class="card-title">Decoder Confidence</div>
                <div class="card-value" style="color: var(--accent-cyan);">
                    {{ summary.average_confidence }}
                </div>
                <div class="card-desc">Mean model output (Nominal threshold is &ge; 0.70)</div>
            </div>

            <div class="card">
                <div class="card-title">Stimulation Therapy</div>
                <div class="card-value" style="color: {% if summary.therapy_enabled %}var(--accent-cyan){% else %}var(--accent-secondary){% endif %};">
                    {{ "ACTIVE" if summary.therapy_enabled else "SUSPENDED" }}
                </div>
                <div class="card-desc">
                    {% if summary.therapy_enabled %}
                    Delivering {{ summary.stimulation_amplitude_ma }} mA @ {{ summary.stimulation_frequency_hz }} Hz
                    {% else %}
                    Stimulator currently suspended due to alarms
                    {% endif %}
                </div>
            </div>
            
            {% if summary.security_active %}
            <div class="card" style="border-color: var(--accent-green);">
                <div class="card-title">Security Shield</div>
                <div class="card-value" style="color: var(--accent-green);">
                    ACTIVE
                </div>
                <div class="card-desc">Intrusions Blocked: <strong>{{ summary.blocked_attacks_count }}</strong></div>
                <div class="card-desc">MTU Abuses Blocked: <strong>{{ summary.blocked_mtu_abuses }}</strong></div>
                {% if summary.p300_leakage_events is defined %}
                <div class="card-desc">P300 Leakage Events: <strong>{{ summary.p300_leakage_events }}</strong></div>
                {% endif %}
            </div>
            {% endif %}
        </div>
        
        <!-- ISO 14971 Risk Evaluation -->
        <div class="card" style="margin-bottom: 2rem; border-color: {% if summary.iso_severity == 'CATASTROPHIC' or summary.iso_severity == 'CRITICAL' %}var(--accent-red){% else %}var(--border-color){% endif %};">
            <div class="card-title">ISO 14971 Risk Evaluation</div>
            <div style="display: flex; gap: 2.5rem; align-items: center; flex-wrap: wrap;">
                <div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Clinical Hazard State</div>
                    <div style="font-size: 1.4rem; font-weight: 700; color: var(--accent-cyan);">{{ summary.hazard_state or "NOMINAL" }}</div>
                </div>
                <div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">ISO 14971 Severity</div>
                    <div style="font-size: 1.4rem; font-weight: 700; color: {% if summary.iso_severity == 'CATASTROPHIC' %}var(--accent-red){% elif summary.iso_severity == 'CRITICAL' %}var(--accent-yellow){% else %}var(--accent-green){% endif %};">{{ summary.iso_severity or "NEGLIGIBLE" }}</div>
                </div>
                <div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Tissue Damage Risk</div>
                    <div style="font-size: 1.4rem; font-weight: 700; color: {% if summary.tissue_damage_risk == 'HIGH' %}var(--accent-red){% else %}var(--text-primary){% endif %};">{{ summary.tissue_damage_risk or "NONE" }}</div>
                </div>
                <div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Mitigation Action</div>
                    <div style="font-size: 1.4rem; font-weight: 700; color: var(--accent-purple);">{{ summary.clinical_action or "MONITOR" }}</div>
                </div>
            </div>
        </div>

        <div class="chart-section">
            <div class="chart-title">Decoder Confidence Timeline</div>
            {{ svg_chart }}
        </div>

        <div class="table-section">
            <div class="table-title">System Audit Log & State Transitions</div>
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Event / Action</th>
                        <th>Connection</th>
                        <th>Mean Impedance</th>
                        <th>Confidence</th>
                        <th>Therapy</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in history %}
                    <tr>
                        <td>{{ item.time_str }}</td>
                        <td>{{ item.event }}</td>
                        <td>
                            <span class="badge {% if item.connected %}badge-nominal{% else %}badge-alert{% endif %}">
                                {{ "ON" if item.connected else "OFF" }}
                            </span>
                        </td>
                        <td>{{ item.mean_impedance }} kΩ</td>
                        <td>
                            <span class="badge {% if item.decoder_confidence >= 0.7 %}badge-nominal{% else %}badge-warning{% endif %}">
                                {{ "%.2f"|format(item.decoder_confidence) }}
                            </span>
                        </td>
                        <td>
                            <span class="badge {% if item.stimulation_enabled %}badge-nominal{% else %}badge-alert{% endif %}">
                                {{ "Active" if item.stimulation_enabled else "Suspended" }}
                            </span>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

class ReportGenerator:
    def __init__(self, twin: DigitalTwin):
        self.twin = twin

    def generate_svg_chart(self, history: List[Dict[str, Any]]) -> str:
        """Generates a clean inline SVG line graph representing decoder confidence over time."""
        # Frame sizes
        w = 1000
        h = 300
        padding_x = 60
        padding_y = 40
        
        graph_w = w - 2 * padding_x
        graph_h = h - 2 * padding_y

        if not history:
            return f'<svg viewBox="0 0 {w} {h}" class="svg-chart"><text x="100" y="150" fill="#9ca3af">No timeline records</text></svg>'

        # Extract timestamps and confidence
        times = [item["timestamp"] for item in history]
        confidences = [item["decoder_confidence"] for item in history]
        
        start_t = times[0]
        duration = times[-1] - start_t if times[-1] != start_t else 1.0

        points = []
        for i, (t, c) in enumerate(zip(times, confidences)):
            norm_x = (t - start_t) / duration
            x = padding_x + norm_x * graph_w
            # Y goes from top to bottom, so 1.0 confidence is at padding_y, and 0.0 is at h - padding_y
            y = padding_y + (1.0 - c) * graph_h
            points.append((x, y))

        # Generate path string
        path_d = ""
        fill_d = f"M {padding_x} {h - padding_y} "
        
        for i, (x, y) in enumerate(points):
            cmd = "M" if i == 0 else "L"
            path_d += f"{cmd} {x:.1f} {y:.1f} "
            fill_d += f"L {x:.1f} {y:.1f} "
            
        fill_d += f"L {points[-1][0]:.1f} {h - padding_y} Z"

        # Generate vertical grid lines and threshold line (Y at 0.7 confidence)
        threshold_y = padding_y + 0.3 * graph_h  # 1.0 - 0.7 = 0.3
        
        svg_content = f"""
        <svg viewBox="0 0 {w} {h}" width="100%" class="svg-chart" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="glowGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#06b6d4" stop-opacity="1"/>
                    <stop offset="100%" stop-color="#a855f7" stop-opacity="1"/>
                </linearGradient>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#06b6d4" stop-opacity="0.25"/>
                    <stop offset="100%" stop-color="#06b6d4" stop-opacity="0.00"/>
                </linearGradient>
            </defs>
            
            <!-- Axis lines -->
            <line x1="{padding_x}" y1="{padding_y}" x2="{padding_x}" y2="{h - padding_y}" stroke="rgba(255,255,255,0.1)" stroke-width="1" />
            <line x1="{padding_x}" y1="{h - padding_y}" x2="{w - padding_x}" y2="{h - padding_y}" stroke="rgba(255,255,255,0.1)" stroke-width="1" />
            
            <!-- Grid Lines -->
            <line x1="{padding_x}" y1="{padding_y}" x2="{w - padding_x}" y2="{padding_y}" stroke="rgba(255,255,255,0.05)" stroke-width="1" stroke-dasharray="4" />
            <line x1="{padding_x}" y1="{h - padding_y}" x2="{w - padding_x}" y2="{h - padding_y}" stroke="rgba(255,255,255,0.05)" stroke-width="1" />
            
            <!-- Threshold Line (0.70 Confidence) -->
            <line x1="{padding_x}" y1="{threshold_y:.1f}" x2="{w - padding_x}" y2="{threshold_y:.1f}" stroke="#f59e0b" stroke-opacity="0.6" stroke-width="2" stroke-dasharray="5 5" />
            <text x="{w - padding_x + 5}" y="{threshold_y + 4}" fill="#f59e0b" font-family="'Space Grotesk', sans-serif" font-size="11">0.70 Limit</text>

            <!-- Text Labels -->
            <text x="{padding_x - 10}" y="{padding_y + 4}" fill="#9ca3af" font-family="'Space Grotesk', sans-serif" font-size="11" text-anchor="end">1.0</text>
            <text x="{padding_x - 10}" y="{h - padding_y + 4}" fill="#9ca3af" font-family="'Space Grotesk', sans-serif" font-size="11" text-anchor="end">0.0</text>
            <text x="{padding_x}" y="{h - padding_y + 20}" fill="#9ca3af" font-family="'Space Grotesk', sans-serif" font-size="11">Start ({int(duration)}s run)</text>
            <text x="{w - padding_x}" y="{h - padding_y + 20}" fill="#9ca3af" font-family="'Space Grotesk', sans-serif" font-size="11" text-anchor="end">End</text>
            
            <!-- Gradient Area -->
            <path d="{fill_d}" fill="url(#areaGrad)" />
            
            <!-- Main Signal line -->
            <path d="{path_d}" fill="none" stroke="url(#glowGrad)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
            
            <!-- Data Points -->
            {"".join(f'<circle cx="{pt[0]:.1f}" cy="{pt[1]:.1f}" r="4" fill="#06b6d4" stroke="#0b0f19" stroke-width="2"/>' for pt in points)}
        </svg>
        """
        return svg_content

    def compile_report(self, clinical_summary: Dict[str, Any], output_prefix: str, anonymize_exports: bool = False):
        history = self.twin.get_history()
        
        if anonymize_exports:
            from vireon.sdk.anonymizer import NeuroDataAnonymizer
            print("[ReportGenerator] Applying NeuroData Anonymization to exported telemetry...")
            anonymizer = NeuroDataAnonymizer()
            history = anonymizer.anonymize_export(history)
            risk_score = anonymizer.scorer.score_risk(history)
            clinical_summary["reid_risk_score"] = risk_score
            print(f"[ReportGenerator] Re-identification Risk Score: {risk_score:.2f}")
            
        # Prepare processed history timeline
        processed_history = []
        for item in history:
            time_str = time.strftime('%H:%M:%S', time.localtime(item["timestamp"]))
            # Calculate mean impedance
            impedances = item["electrode_impedances"].values()
            mean_imp = round(sum(impedances) / len(impedances), 2) if impedances else 0.0
            
            processed_history.append({
                "time_str": time_str,
                "event": item["event"],
                "connected": item["connected"],
                "mean_impedance": mean_imp,
                "decoder_confidence": item["decoder_confidence"],
                "stimulation_enabled": item["stimulation_enabled"]
            })

        # Save HTML Report
        svg_chart = Markup(self.generate_svg_chart(history))
        date_str = time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime())
        
        env = Environment(loader=BaseLoader(), autoescape=select_autoescape(['html', 'xml']))
        template = env.from_string(HTML_TEMPLATE)
        html_output = template.render(
            date_str=date_str,
            summary=clinical_summary,
            history=processed_history,
            svg_chart=svg_chart
        )
        
        html_file = f"{output_prefix}_report.html"
        with open(html_file, "w") as f:
            f.write(html_output)
        print(f"[ReportGenerator] Saved HTML report to {html_file}")

        # Try to generate PDF report if weasyprint is available
        try:
            from weasyprint import HTML, default_url_fetcher
            
            def block_external_fetcher(url):
                if url.startswith('file://') or url.startswith('data:'):
                    return default_url_fetcher(url)
                print(f"[Security] Blocked WeasyPrint external fetch: {url}")
                return None

            pdf_file = f"{output_prefix}_report.pdf"
            HTML(string=html_output, url_fetcher=block_external_fetcher).write_pdf(pdf_file)
            print(f"[ReportGenerator] Saved PDF report to {pdf_file}")
        except ImportError:
            print("[ReportGenerator] weasyprint not installed. Skipping PDF generation.")
        except Exception as e:
            print(f"[ReportGenerator] Failed to generate PDF: {e}")

        # Save Markdown Report
        md_output = self._compile_markdown(clinical_summary, processed_history)
        md_file = f"{output_prefix}_report.md"
        with open(md_file, "w") as f:
            f.write(md_output)
        print(f"[ReportGenerator] Saved Markdown report to {md_file}")

        # Save JSON telemetry database
        json_file = f"{output_prefix}_telemetry.json"
        with open(json_file, "w") as f:
            json.dump(history, f, indent=2)
        print(f"[ReportGenerator] Saved JSON telemetry database to {json_file}")

    def _compile_markdown(self, summary: Dict[str, Any], history: List[Dict[str, Any]]) -> str:
        md = []
        md.append("# VIREON Software Audit & Clinical Integrity Report")
        md.append(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
        md.append(f"**Device ID:** {summary['device_id']}")
        md.append("")
        md.append("## Executive Clinical Summary")
        md.append(f"- **Clinical Status:** `{summary['current_status']}`")
        md.append(f"- **Alert Active:** `{summary['alert_active']}`")
        md.append(f"- **Therapy Delivered:** `{summary['therapy_enabled']}`")
        md.append(f"- **Therapy Amplitude:** `{summary['stimulation_amplitude_ma']} mA`")
        md.append(f"- **Therapy Frequency:** `{summary['stimulation_frequency_hz']} Hz`")
        md.append(f"- **Average Decoder Confidence:** `{summary['average_confidence']}`")
        md.append(f"- **Minimum Decoder Confidence:** `{summary['min_confidence']}`")
        md.append("")
        if summary.get("security_active"):
            md.append("## Neuro Security Shield Audit")
            md.append("- **Security Status:** `ACTIVE` (IDS/IPS Enabled)")
            md.append(f"- **Blocked Intrusions:** `{summary.get('blocked_attacks_count', 0)}`")
            md.append(f"- **MTU Abuses Blocked:** `{summary.get('blocked_mtu_abuses', 0)}`")
            if 'p300_leakage_events' in summary:
                md.append(f"- **P300 Leakage Events:** `{summary.get('p300_leakage_events', 0)}`")
            md.append("")
        md.append("## ISO 14971 Medical Device Risk Classification")
        md.append(f"- **Clinical Hazard State:** `{summary.get('hazard_state', 'NOMINAL')}`")
        md.append(f"- **ISO 14971 Severity:** `{summary.get('iso_severity', 'NEGLIGIBLE')}`")
        md.append(f"- **Tissue Damage Risk:** `{summary.get('tissue_damage_risk', 'NONE')}`")
        md.append(f"- **Recommended Mitigation Action:** `{summary.get('clinical_action', 'MONITOR')}`")
        md.append("")
        md.append("## System Audit Log")
        md.append("| Timestamp | Event / Action | Link | Mean Impedance | Confidence | Therapy Status |")
        md.append("| --- | --- | --- | --- | --- | --- |")
        for item in history:
            link = "UP" if item["connected"] else "DOWN"
            therapy = "Active" if item["stimulation_enabled"] else "Suspended"
            md.append(f"| {item['time_str']} | {item['event']} | {link} | {item['mean_impedance']} kΩ | {item['decoder_confidence']:.2f} | {therapy} |")
        return "\n".join(md)
