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
import time
import threading
import os
import sys

# Ensure vireon is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from vireon.core.state_store import StateStore
from vireon.engine.engine import ReplayEngine
from vireon.core.detection import SecurityEngine
from vireon_lab.core_examples.clinical import NeuroIPS
from vireon.validation.threat_intel import ThreatIntelligence
from vireon.core.attack import SignalAttackEngine

st.set_page_config(page_title="VIREON Dashboard", layout="wide", page_icon="🧠")

@st.cache_resource
def init_system():
    # Initialize components
    twin = DigitalTwin(hardware_mode=False) # Start in synth mode
    ids = SecurityEngine(twin)
    ips = NeuroIPS(twin, ids)
    ti = ThreatIntelligence(registry_path="vireon/core/data/cptara_stub.json")
    attack_engine = SignalAttackEngine(twin)
    
    engine = ReplayEngine(twin=twin, attack_engine=attack_engine)
    engine.last_anomaly_score = 0.0
    engine.active_anomalies = []
    
    def ui_callback(data):
        if data.shape[1] > 0:
            anomalies = ids.analyze_signal(data)
            score = ids.score_signal(data)
            engine.last_anomaly_score = score
            engine.active_anomalies = anomalies
            # Apply IPS
            ips.sanitize_stimulation_write(twin.stimulation_amplitude_ma, twin.stimulation_frequency_hz)
            ips.mitigate_signal_anomalies(data, anomalies)
            
    engine.add_callback(ui_callback)
    
    # Create a background thread for the engine
    engine_thread = threading.Thread(target=engine.run, daemon=True)
    engine_thread.start()
    
    return twin, engine, attack_engine, ti

twin, engine, attack_engine, ti = init_system()

# --- Sidebar Controls ---
st.sidebar.title("VIREON Control")

st.sidebar.subheader("Therapy / Stimulation")
stim_enabled = st.sidebar.checkbox("Enable Stimulation", value=twin.stimulation_enabled)
amp_ma = st.sidebar.slider("Amplitude (mA)", 0.0, 10.0, float(twin.stimulation_amplitude_ma), 0.1)
freq_hz = st.sidebar.slider("Frequency (Hz)", 0.0, 200.0, float(twin.stimulation_frequency_hz), 1.0)

if stim_enabled != twin.stimulation_enabled:
    twin.update_therapy(stim_enabled)
if stim_enabled:
    twin.update_stimulation_params(amp_ma, freq_hz)

st.sidebar.subheader("Attack Injection")
attack_options = ["none", "noise", "drift", "temporal_evasion", "session_replay"]
selected_attack = st.sidebar.selectbox("Inject Attack", attack_options)

if st.sidebar.button("Apply Attack"):
    engine.inject_attack(selected_attack)

# --- Main Dashboard ---
st.title("VIREON Live Dashboard")

# Fetch current state
state = twin.get_state()

# Metrics Row
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Battery", f"{state['battery_level']:.1f}%")
col2.metric("Neural Coherence", f"{state['neural_coherence']:.3f}")
col3.metric("Beta Power", f"{state['beta_power']:.1f}")

# Get the latest buffer from engine for plotting
buffer = engine.get_buffer()
if buffer is not None and buffer.shape[1] > 0:
    anomaly_score = engine.last_anomaly_score
    is_anomaly = anomaly_score > 0.08 # Visual threshold
    
    col4.metric("Anomaly Score", f"{anomaly_score:.3f}", delta="High Risk!" if is_anomaly else "Normal", delta_color="inverse")
    col5.metric("NISS Score", f"{state['niss_score']}")
    
    # EEG Plotting
    st.subheader("Live EEG Stream (8 Channels)")
    # Just take the last 100 samples to keep UI fast
    plot_len = min(100, buffer.shape[1])
    eeg_data = buffer[:, -plot_len:]
    df = pd.DataFrame(eeg_data.T, columns=[f"Ch {i+1}" for i in range(8)])
    st.line_chart(df)
else:
    st.info("Waiting for data buffer...")

# Threat Intel Area
st.subheader("Active Threat Intelligence")
if state["clinical_alert_active"] and engine.active_attack != "none":
    st.error(f"ALERT: {state['clinical_status']}")
    
    threat_info = ti.resolve_attack(engine.active_attack)
    if threat_info:
        if "cwe" in threat_info:
            st.write(f"**CWE**: {threat_info['cwe']}")
        if "stride" in threat_info:
            st.write(f"**STRIDE**: {threat_info['stride']}")
        if "mitre_attack" in threat_info:
            st.write(f"**MITRE ATT&CK**: {threat_info['mitre_attack']}")
        if "iso_14971_category" in threat_info:
            st.write(f"**ISO 14971**: {threat_info['iso_14971_category']}")
        st.write(f"**Name**: {threat_info['name']}")
        st.write(f"**Severity**: {threat_info['severity']}")
        st.write(f"**Description**: {threat_info['description']}")
else:
    st.success("System Nominal. No active threats detected.")

# Auto-refresh mechanism
time.sleep(0.5)
st.rerun()
