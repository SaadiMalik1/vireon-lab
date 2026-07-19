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

from vireon.services.engine import ReplayEngine
from vireon.reference_providers.ids.detection import SecurityEngine
from vireon.reference_providers.clinical.neuroips import NeuroIPS
from vireon.libraries.stix.threat_intel import ThreatIntelligence
from vireon.libraries.attack_factory.attack.engine import SignalAttackEngine
from vireon.sdk.state import IStateStore
from vireon.runtime.state_store import StateStore
from vireon.sdk.events import IEventBus
from vireon.runtime.event_bus import EventBus
from vireon.reference_providers.physics.physics import PhysicsEngine
from vireon.reference_providers.physics.dynamics import KuramotoModel

st.set_page_config(page_title="VIREON Dashboard", layout="wide", page_icon="🧠")

@st.cache_resource
def init_system():
    # Initialize components
    event_bus = EventBus()
    state_store = StateStore(event_bus)
    
    # Pre-populate state for dashboard compatibility
    state_store.set("battery_level", 100.0)
    state_store.set("neural_coherence", 0.95)
    state_store.set("beta_power", 25.0)
    state_store.set("niss_score", 0)
    state_store.set("clinical_alert_active", False)
    state_store.set("clinical_status", "Nominal")
    state_store.set("decoder_confidence", 0.99)
    state_store.set("stimulation_enabled", False)
    state_store.set("stimulation_amplitude_ma", 0.0)
    state_store.set("stimulation_frequency_hz", 0.0)
    state_store.set("temperature_celsius", 37.0)
    
    # Provide the mock state store to components
    # The real physics engine will update the state store
    
    # In a full migration, physics_engine would publish to state_store. 
    # Since the physics engine doesn't take state_store yet, we'll manually push to state_store in the UI loop
    
    ids = SecurityEngine(state_store)
    ips = NeuroIPS(state_store, ids, event_bus)
    ti = ThreatIntelligence(registry_path="vireon/libraries/stix/data/stride_threats.json") # Updated path
    attack_engine = SignalAttackEngine(state_store, event_bus)
    
    # We pass the state_store and physics to the engine directly
    engine = ReplayEngine(state_store=state_store, attack_engine=attack_engine)
    engine.last_anomaly_score = 0.0
    engine.active_anomalies = []
    
    def ui_callback(data):
        if data.shape[1] > 0:
            anomalies = ids.analyze_signal(data)
            score = ids.score_signal(data)
            engine.last_anomaly_score = score
            engine.active_anomalies = anomalies
            # Apply IPS
            amp = state_store.get("stimulation_amplitude_ma", 0.0)
            freq = state_store.get("stimulation_frequency_hz", 0.0)
            ips.sanitize_stimulation_write(amp, freq)
            ips.mitigate_signal_anomalies(data, anomalies)
            
            # Simple simulation for dashboard
            state_store.set("beta_power", float(np.mean(np.abs(data))))
            
    engine.add_callback(ui_callback)
    
    # Start the replay engine (it creates its own thread)
    engine.start()
    
    return state_store, engine, attack_engine, ti

state_store, engine, attack_engine, ti = init_system()

# --- Sidebar Controls ---
st.sidebar.title("VIREON Control")

st.sidebar.subheader("Therapy / Stimulation")
stim_enabled = st.sidebar.checkbox("Enable Stimulation", value=state_store.get("stimulation_enabled", False))
amp_ma = st.sidebar.slider("Amplitude (mA)", 0.0, 10.0, float(state_store.get("stimulation_amplitude_ma", 0.0)), 0.1)
freq_hz = st.sidebar.slider("Frequency (Hz)", 0.0, 200.0, float(state_store.get("stimulation_frequency_hz", 0.0)), 1.0)

if stim_enabled != state_store.get("stimulation_enabled", False):
    state_store.set("stimulation_enabled", stim_enabled, "ui")
if stim_enabled:
    state_store.set("stimulation_amplitude_ma", amp_ma, "ui")
    state_store.set("stimulation_frequency_hz", freq_hz, "ui")

st.sidebar.subheader("Attack Injection")
attack_options = ["none", "noise", "drift", "temporal_evasion", "session_replay"]
selected_attack = st.sidebar.selectbox("Inject Attack", attack_options)

if st.sidebar.button("Apply Attack"):
    engine.inject_attack(selected_attack)

# --- Main Dashboard ---
st.title("VIREON Live Dashboard")

# Fetch current state
state = state_store.get_all()

# Metrics Row
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Battery", f"{state.get('battery_level', 100.0):.1f}%")
col2.metric("Neural Coherence", f"{state.get('neural_coherence', 0.95):.3f}")
col3.metric("Beta Power", f"{state.get('beta_power', 25.0):.1f}")

# Get the latest buffer from engine for plotting
buffer = engine.get_buffer()
if buffer is not None and buffer.shape[1] > 0:
    anomaly_score = engine.last_anomaly_score
    is_anomaly = anomaly_score > 0.08 # Visual threshold
    
    col4.metric("Anomaly Score", f"{anomaly_score:.3f}", delta="High Risk!" if is_anomaly else "Normal", delta_color="inverse")
    col5.metric("NISS Score", f"{state.get('niss_score', 0)}")
    
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
if state.get("clinical_alert_active", False) and engine.active_attack != "none":
    st.error(f"ALERT: {state.get('clinical_status', 'Nominal')}")
    
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
