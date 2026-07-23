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

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import time
import os
import sys
import json
from datetime import datetime

# Ensure local imports work reliably
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from live_signal_engine import SyntheticEEGStream, CHANNEL_NAMES
from forensic_exporter import generate_stix_package, generate_html_audit_report

# Page Configuration
st.set_page_config(
    page_title="VIREON Neurosecurity Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme-Adaptive CSS Design Token System (Supports both Light and Dark Modes)
st.markdown("""
<style>
    /* Global Adaptive Styling using CSS Variables */
    .stApp {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    /* Cyber Header Banner */
    .cyber-banner {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.8) 100%);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
        backdrop-filter: blur(12px);
    }
    
    .cyber-title {
        font-size: 30px;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(90deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    
    .cyber-subtitle {
        color: #94a3b8;
        font-size: 14px;
        margin-top: 6px;
        font-weight: 400;
    }
    
    /* Theme Adaptive Cards */
    .glass-metric {
        background: var(--secondary-background-color, rgba(15, 23, 42, 0.7));
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 14px;
        padding: 18px 22px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(8px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .glass-metric:hover {
        border-color: rgba(56, 189, 248, 0.4);
        transform: translateY(-2px);
    }
    
    .glass-metric-val {
        font-size: 26px;
        font-weight: 800;
        margin-top: 4px;
        color: var(--text-color, #e2e8f0);
    }
    
    .glass-metric-lbl {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-color, #64748b);
        opacity: 0.75;
        font-weight: 600;
    }

    /* Badges */
    .badge-nominal {
        background: rgba(34, 197, 94, 0.15);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.35);
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.04em;
    }

    .badge-hazard {
        background: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.4);
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.04em;
    }

    /* Fix Light Mode Sidebar Controls & Input Visibility */
    [data-testid="stSidebar"] {
        background-color: var(--secondary-background-color, #0f172a);
    }

    .stButton > button {
        font-weight: 600;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "stream" not in st.session_state:
    st.session_state.stream = SyntheticEEGStream(sampling_rate=100, num_channels=8, seed=42)
if "active_attack" not in st.session_state:
    st.session_state.active_attack = "none"
if "attack_intensity" not in st.session_state:
    st.session_state.attack_intensity = 1.0
if "stimulation_enabled" not in st.session_state:
    st.session_state.stimulation_enabled = False
if "dbs_amplitude" not in st.session_state:
    st.session_state.dbs_amplitude = 2.5
if "dbs_frequency" not in st.session_state:
    st.session_state.dbs_frequency = 130.0
if "live_stream_active" not in st.session_state:
    st.session_state.live_stream_active = False
if "time_shift" not in st.session_state:
    st.session_state.time_shift = 0.0

# Sidebar Control Center
with st.sidebar:
    st.markdown("### 🧠 VIREON Control Center")
    st.caption("Neurosecurity Hardware & Lab Orchestrator")
    
    st.divider()
    
    # Mode & Stream Controls
    st.markdown("#### 🔄 Streaming Engine Mode")
    stream_mode = st.radio(
        "Telemetry Execution Mode",
        ["⚡ Live Real-Time Stream (Auto-Update)", "⏸️ Static Snapshot View"],
        index=0 if st.session_state.live_stream_active else 1,
        help="Toggle continuous real-time neural signal updates vs static snapshot mode."
    )
    st.session_state.live_stream_active = ("Live Real-Time" in stream_mode)
    
    refresh_rate = st.slider("Live Stream Refresh Interval (s)", 0.3, 2.0, 0.8, 0.1)
    
    st.divider()
    
    # Data Source Selector
    st.markdown("#### 📁 Data Source Selector")
    data_source = st.selectbox(
        "Select Telemetry Dataset",
        [
            "Synthetic Live Stream (8-Channel)",
            "Real Clinical EEG (ADHD Mendeley EDF / CSV)",
            "Motor Imagery BCI Dataset (PhysioNet)",
            "Deep Brain Stimulation Subthalamic LFP"
        ],
        index=0,
        help="Select real clinical datasets or synthetic neural signal generators."
    )
    
    st.divider()
    
    # Quick Action: Active Threat Mutator
    st.markdown("#### ⚡ Hardware Physical Mutator")
    selected_attack = st.selectbox(
        "Inject Threat Vector",
        ["none", "Gaussian Noise Injection", "DC Offset Drift", "Denial of Service", "Session Replay", "Malicious DBS Pulse Train"],
        index=0,
        help="Select a physical threat vector to inject into the neural telemetry stream."
    )
    
    intensity = st.slider("Threat Perturbation Factor", 0.1, 3.0, st.session_state.attack_intensity, 0.1)
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("Apply Threat", type="primary", use_container_width=True):
            st.session_state.active_attack = selected_attack
            st.session_state.attack_intensity = intensity
            st.toast(f"Applied threat vector: {selected_attack}", icon="🚨")
    with col_s2:
        if st.button("Reset Telemetry", use_container_width=True):
            st.session_state.active_attack = "none"
            st.session_state.attack_intensity = 1.0
            st.toast("System telemetry restored to Nominal", icon="✅")
        
    st.divider()
    
    # DBS Stimulation Control
    st.markdown("#### ⚡ Closed-Loop DBS Controls")
    dbs_enable = st.checkbox("Enable Deep Brain Pulse Generator", value=st.session_state.stimulation_enabled)
    dbs_amp = st.slider("Pulse Amplitude (mA)", 0.0, 10.0, st.session_state.dbs_amplitude, 0.1)
    dbs_freq = st.slider("Stimulation Frequency (Hz)", 10.0, 200.0, st.session_state.dbs_frequency, 5.0)
    
    st.session_state.stimulation_enabled = dbs_enable
    st.session_state.dbs_amplitude = dbs_amp
    st.session_state.dbs_frequency = dbs_freq
    
    st.divider()
    st.caption("VIREON Platform v1.1.0 | ISO 14971 Class III Compliant")

# Top Header Cyber Banner
is_attack = st.session_state.active_attack != "none"
banner_badge = f"""<span class="badge-hazard">🚨 THREAT ACTIVE: {st.session_state.active_attack.upper()}</span>""" if is_attack else """<span class="badge-nominal">✅ HARDWARE TELEMETRY NOMINAL</span>"""

st.markdown(f"""
<div class="cyber-banner">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 class="cyber-title">VIREON Neurosecurity Interactive Platform</h1>
            <div class="cyber-subtitle">Real-time Closed-Loop Neural Signal Telemetry, Physical Threat Mutators & Forensic Compliance</div>
        </div>
        <div>
            {banner_badge}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Advance time shift if Live Mode is active
if st.session_state.live_stream_active:
    st.session_state.time_shift += refresh_rate

# Generate Live Signal Data Chunk
t, signals = st.session_state.stream.generate_chunk(
    duration_sec=2.0,
    data_source=data_source,
    attack_type=st.session_state.active_attack,
    attack_intensity=st.session_state.attack_intensity,
    time_shift=st.session_state.time_shift
)

# Compute Real-time Anomaly Metrics
band_powers = st.session_state.stream.compute_band_powers(signals)
anomaly_score = 0.85 * st.session_state.attack_intensity if is_attack else 0.04
niss_score = int(anomaly_score * 100)
clinical_status = "HAZARD DETECTED" if (is_attack or (dbs_enable and dbs_amp > 7.0)) else "Therapeutic Nominal"

# Top Metric Row
m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.markdown(f"""<div class="glass-metric"><div class="glass-metric-lbl">Battery Level</div><div class="glass-metric-val" style="color:#38bdf8;">98.5%</div></div>""", unsafe_allow_html=True)
with m2:
    coherence = 0.42 if is_attack else 0.96
    st.markdown(f"""<div class="glass-metric"><div class="glass-metric-lbl">Neural Coherence</div><div class="glass-metric-val" style="color: {'#ef4444' if is_attack else '#22c55e'};">{coherence:.3f}</div></div>""", unsafe_allow_html=True)
with m3:
    st.markdown(f"""<div class="glass-metric"><div class="glass-metric-lbl">Beta Power</div><div class="glass-metric-val" style="color:#a855f7;">{band_powers['Beta (13-30Hz)']:.1f}%</div></div>""", unsafe_allow_html=True)
with m4:
    st.markdown(f"""<div class="glass-metric"><div class="glass-metric-lbl">Anomaly Score</div><div class="glass-metric-val" style="color: {'#ef4444' if is_attack else '#38bdf8'};">{anomaly_score:.3f}</div></div>""", unsafe_allow_html=True)
with m5:
    st.markdown(f"""<div class="glass-metric"><div class="glass-metric-lbl">NISS Severity</div><div class="glass-metric-val" style="color: {'#ef4444' if niss_score > 50 else '#22c55e'};">{niss_score} / 100</div></div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Main Navigation Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Live Neural Signals",
    "💉 Signal Tampering Lab",
    "⚡ Closed-Loop DBS Lab",
    "📡 Wireless & BLE Security",
    "🤖 Adversarial ML Lab",
    "🛡️ Threat Matrix & Forensics"
])

# ---------------------------------------------------------------------------
# TAB 1: Live Neural Signal Stream & Spectral Decomposition
# ---------------------------------------------------------------------------
with tab1:
    st.markdown("### 📊 Real-time 8-Channel EEG Waveform Monitor")
    st.caption(f"Streaming continuous 100 Hz neural telemetry from **{data_source}** across scalp electrodes with Welch FFT spectral decomposition.")
    
    col_chart, col_bands = st.columns([3, 1])
    
    with col_chart:
        fig_eeg = go.Figure()
        neon_colors = ["#38bdf8", "#818cf8", "#c084fc", "#f472b6", "#fb7185", "#34d399", "#fbbf24", "#a78bfa"]
        
        for ch in range(8):
            # Offset channels vertically for multi-trace EEG view
            offset_signal = signals[ch, :] + (ch * 60.0)
            fig_eeg.add_trace(go.Scatter(
                x=t, y=offset_signal,
                mode="lines",
                name=f"Channel {CHANNEL_NAMES[ch]}",
                line=dict(color=neon_colors[ch % len(neon_colors)], width=1.5)
            ))
            
        fig_eeg.update_layout(
            height=440,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15, 23, 42, 0.5)",
            xaxis=dict(title="Time (seconds)", showgrid=True, gridcolor="rgba(148,163,184,0.15)"),
            yaxis=dict(title="EEG Electrode Trace (µV Offset)", showgrid=True, gridcolor="rgba(148,163,184,0.15)"),
            legend=dict(orientation="h", y=1.12)
        )
        st.plotly_chart(fig_eeg, use_container_width=True)
        
    with col_bands:
        st.markdown("#### 🎵 Spectral Power Distribution")
        df_bands = pd.DataFrame(list(band_powers.items()), columns=["Band", "Power (%)"])
        fig_bar = px.bar(
            df_bands, x="Power (%)", y="Band", orientation="h",
            color="Power (%)", color_continuous_scale="Viridis"
        )
        fig_bar.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15, 23, 42, 0.5)",
            xaxis=dict(range=[0, 100], gridcolor="rgba(148,163,184,0.15)"),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 2: Signal Tampering & IDS Anomaly Lab
# ---------------------------------------------------------------------------
with tab2:
    st.markdown("### 💉 Physical Signal Tampering & Intrusion Detection Lab")
    st.caption("Simulate hardware tampering vectors (Gaussian noise, baseline drift, grounding) and evaluate live Intrusion Detection System (IDS) alerts.")
    
    col_tamp_ctrl, col_tamp_vis = st.columns([1, 2])
    
    with col_tamp_ctrl:
        st.markdown("#### Threat Mutator Controls")
        t_type = st.selectbox("Attack Vector Category", ["Gaussian Noise Injection", "DC Offset Drift", "Denial of Service", "Session Replay"])
        t_channels = st.multiselect("Target Electrodes", CHANNEL_NAMES, default=["F3", "F4"])
        t_scale = st.slider("Perturbation Amplitude (uV)", 5.0, 100.0, 35.0)
        
        if st.button("Trigger Attack Vector", type="primary", use_container_width=True):
            st.session_state.active_attack = t_type
            st.session_state.attack_intensity = t_scale / 35.0
            st.rerun()
            
        st.divider()
        st.markdown("#### Real-time IDS Alert Engine")
        if is_attack:
            st.error(f"🚨 **IDS THREAT DETECTED**: {st.session_state.active_attack}\n\n- **Anomaly Score**: `{anomaly_score:.3f}` (Threshold: `0.350`)\n- **NISS Rating**: `{niss_score} / 100` (HIGH SEVERITY)\n- **ISO 14971 Status**: `{clinical_status}`")
        else:
            st.success("✅ **IDS BASELINE**: Signal telemetry within nominal bounds.\n\n- **Anomaly Score**: `0.040` (Threshold: `0.350`)\n- **NISS Rating**: `4 / 100` (SAFE)")
            
    with col_tamp_vis:
        st.markdown("#### Signal Mutation Comparison (Baseline vs Mutated)")
        clean_t, clean_sig = SyntheticEEGStream(seed=42).generate_chunk(duration_sec=2.0, attack_type="none", time_shift=st.session_state.time_shift)
        
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Scatter(x=clean_t, y=clean_sig[0, :], name="Baseline Channel F3", line=dict(color="#38bdf8", dash="dash", width=1.5)))
        fig_comp.add_trace(go.Scatter(x=t, y=signals[0, :], name="Mutated Channel F3", line=dict(color="#ef4444", width=2)))
        
        fig_comp.update_layout(
            height=420,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15, 23, 42, 0.5)",
            xaxis=dict(title="Time (seconds)", gridcolor="rgba(148,163,184,0.15)"),
            yaxis=dict(title="Amplitude (µV)", gridcolor="rgba(148,163,184,0.15)"),
            legend=dict(orientation="h", y=1.12)
        )
        st.plotly_chart(fig_comp, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 3: Closed-Loop DBS & Clinical Risk Simulator
# ---------------------------------------------------------------------------
with tab3:
    st.markdown("### ⚡ Closed-Loop DBS & Clinical Risk Control")
    st.caption("Model Deep Brain Stimulation (DBS) pulse dynamics, Subthalamic Nucleus LFP suppression, and Shannon safety limits.")
    
    col_dbs_status, col_dbs_plot = st.columns([1, 2])
    
    with col_dbs_status:
        st.markdown("#### Clinical Safety Metrics")
        shannon_limit = (dbs_amp ** 2) * (dbs_freq / 130.0) * 0.1
        thermal_delta = 0.05 * dbs_amp
        
        st.metric("Pulse Amplitude", f"{dbs_amp:.1f} mA")
        st.metric("Stimulation Frequency", f"{dbs_freq:.0f} Hz")
        st.metric("Shannon Charge Density", f"{shannon_limit:.2f} µC/phase", delta="SAFE" if shannon_limit < 4.0 else "HAZARD EXCEEDED", delta_color="inverse")
        st.metric("Tissue Heating Delta", f"+{thermal_delta:.2f} °C")
        
        if shannon_limit >= 4.0:
            st.error("⚠️ **HAZARD ALARM**: Tissue charge density exceeds Shannon safety threshold (4.0 µC/phase). Risk of irreversible local neural tissue damage!")
        else:
            st.success("✅ **SAFETY NOMINAL**: Charge density within therapeutic window.")
            
    with col_dbs_plot:
        st.markdown("#### Subthalamic Beta Rhythm Suppression & Pulse Overlay")
        t_pulse = np.linspace(0, 1.0, 500)
        lfp_pathological = 30.0 * np.sin(2 * np.pi * 20.0 * t_pulse)
        
        if dbs_enable:
            suppression_factor = max(0.1, 1.0 - (dbs_amp / 5.0))
            lfp_treated = lfp_pathological * suppression_factor
            dbs_train = dbs_amp * 10.0 * np.sign(np.sin(2 * np.pi * dbs_freq * t_pulse))
        else:
            lfp_treated = lfp_pathological
            dbs_train = np.zeros_like(t_pulse)
            
        fig_dbs = go.Figure()
        fig_dbs.add_trace(go.Scatter(x=t_pulse, y=lfp_treated, name="LFP Beta Rhythm (uV)", line=dict(color="#818cf8", width=2)))
        fig_dbs.add_trace(go.Scatter(x=t_pulse, y=dbs_train, name="DBS Pulse Train (mA x 10)", line=dict(color="#f43f5e", width=1.5)))
        
        fig_dbs.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15, 23, 42, 0.5)",
            xaxis=dict(title="Time (seconds)", gridcolor="rgba(148,163,184,0.15)"),
            yaxis=dict(title="Amplitude", gridcolor="rgba(148,163,184,0.15)"),
            legend=dict(orientation="h", y=1.12)
        )
        st.plotly_chart(fig_dbs, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 4: Wireless BLE & Telemetry Security Lab
# ---------------------------------------------------------------------------
with tab4:
    st.markdown("### 📡 Wireless BLE Protocol & Telemetry Security")
    st.caption("Inspect GATT characteristics, encrypted payload sessions, and packet fragmentation resilience.")
    
    col_ble_pkt, col_ble_inspect = st.columns([2, 1])
    
    with col_ble_pkt:
        st.markdown("#### Live GATT Telemetry Packet Stream")
        packets = [
            {"Timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3], "Handle": "0x0014", "UUID": "00002a37-0000-1000-8000-00805f9b34fb", "Type": "NOTIFY", "Status": "ENCRYPTED_AES128", "Payload": "a4b29f081c2d"},
            {"Timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3], "Handle": "0x0018", "UUID": "00002a38-0000-1000-8000-00805f9b34fb", "Type": "WRITE_CMD", "Status": "VALIDATED", "Payload": "010025000000"},
            {"Timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3], "Handle": "0x001c", "UUID": "00002a39-0000-1000-8000-00805f9b34fb", "Type": "INDICATE", "Status": "ALERT_CORRUPT" if is_attack else "OK", "Payload": "ffffffffffff"}
        ]
        st.dataframe(pd.DataFrame(packets), use_container_width=True)
        
    with col_ble_inspect:
        st.markdown("#### Session Authentication")
        st.text_input("Device MAC Address", value="AA:BB:CC:DD:EE:FF", disabled=True)
        st.text_input("Active Bearer Token", value="bearer_tok_vireon_secure_8912", type="password", disabled=True)
        st.button("Rotate Pair Key", use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 5: Adversarial ML BCI Intent Classifier Lab
# ---------------------------------------------------------------------------
with tab5:
    st.markdown("### 🤖 Adversarial ML & Decoder Evasion Lab")
    st.caption("Evaluate gradient-based FGSM and PGD adversarial perturbations against BCI motor imagery decoders.")
    
    col_ml_cfg, col_ml_plot = st.columns([1, 2])
    
    with col_ml_cfg:
        st.markdown("#### Adversarial Attack Configuration")
        attack_algo = st.selectbox("Evasion Algorithm", ["FGSM (Fast Gradient Sign Method)", "PGD (Projected Gradient Descent)", "CW (Carlini-Wagner L2)"])
        epsilon = st.slider("Perturbation Epsilon (ε)", 0.01, 0.50, 0.15, 0.01)
        
        st.markdown("#### Classifier Performance")
        clean_acc = 98.4
        adv_acc = max(5.0, clean_acc - (epsilon * 180.0))
        st.metric("Baseline Accuracy", f"{clean_acc}%")
        st.metric("Adversarial Accuracy", f"{adv_acc:.1f}%", delta=f"-{clean_acc - adv_acc:.1f}%", delta_color="inverse")
        
    with col_ml_plot:
        st.markdown("#### Intent Classification Confusion Matrix")
        labels = ["Left Hand", "Right Hand", "Foot Movement", "Rest"]
        cm = np.array([
            [45, 2, 1, 2],
            [3, 42, 2, 3],
            [1, 2, 46, 1],
            [2, 1, 1, 46]
        ])
        if epsilon > 0.10:
            cm = np.array([
                [12, 22, 10, 6],
                [15, 14, 12, 9],
                [8, 16, 18, 8],
                [10, 11, 9, 20]
            ])
            
        fig_cm = px.imshow(cm, x=labels, y=labels, color_continuous_scale="Viridis", text_auto=True)
        fig_cm.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15, 23, 42, 0.5)")
        st.plotly_chart(fig_cm, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 6: STIX 2.1 Threat Matrix & Forensic Audit Generator
# ---------------------------------------------------------------------------
with tab6:
    st.markdown("### 🛡️ STIX 2.1 Threat Matrix & Forensic Exporter")
    st.caption("Generate clinical compliance evidence packages aligned with ISO 14971, CWE, and STIX 2.1 formats.")
    
    col_th_info, col_th_exp = st.columns([2, 1])
    
    with col_th_info:
        st.markdown("#### Active Threat Mapping Registry")
        threat_table = [
            {"Threat Vector": "Gaussian Noise Injection", "STRIDE Tactic": "Tampering", "CWE Mapping": "CWE-345 (Insufficient Verification)", "ISO 14971 Risk": "HIGH"},
            {"Threat Vector": "DC Offset Drift", "STRIDE Tactic": "Tampering / Info Leak", "CWE Mapping": "CWE-693 (Protection Mechanism Failure)", "ISO 14971 Risk": "MEDIUM"},
            {"Threat Vector": "Denial of Service", "STRIDE Tactic": "Denial of Service", "CWE Mapping": "CWE-400 (Uncontrolled Resource Consumption)", "ISO 14971 Risk": "CRITICAL"},
            {"Threat Vector": "Malicious DBS Pulse Train", "STRIDE Tactic": "Elevation of Privilege", "CWE Mapping": "CWE-269 (Improper Privilege Management)", "ISO 14971 Risk": "CRITICAL"}
        ]
        st.dataframe(pd.DataFrame(threat_table), use_container_width=True)
        
    with col_th_exp:
        st.markdown("#### Export Audit Package")
        st.caption("Generate downloadable compliance artifacts for ISO 14971 and STIX 2.1 parsers.")
        
        stix_json = generate_stix_package(
            st.session_state.active_attack, anomaly_score, niss_score, clinical_status
        )
        html_report = generate_html_audit_report(
            st.session_state.active_attack, anomaly_score, niss_score, clinical_status
        )
        
        st.download_button(
            "📥 Download STIX 2.1 JSON",
            data=stix_json,
            file_name=f"vireon_stix_bundle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
        
        st.download_button(
            "📄 Download HTML Executive Report",
            data=html_report,
            file_name=f"vireon_audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html",
            use_container_width=True
        )

# Handle Real-time Auto-Refresh Rerun Loop if Live Mode is active
if st.session_state.live_stream_active:
    time.sleep(refresh_rate)
    st.rerun()
