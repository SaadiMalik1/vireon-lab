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

"""
VIREON Neurotech & Neurosecurity Educational Academy Module.
Provides interactive tooltips, DSP math breakdowns, STRIDE / MITRE ATLAS matrices,
and links to local documentation/lessons.
"""

import streamlit as st
import pandas as pd

DOCS_BASE_URL = "http://127.0.0.1:8008"

def render_dsp_education_expander():
    """Renders interactive educational accordion for Digital Signal Processing."""
    with st.expander("ACADEMY: DIGITAL SIGNAL PROCESSING (DSP) & WELCH PSD", expanded=False):
        st.markdown(rf"""
        ### Understanding Neural Signal Telemetry
        
        Neural signals measured via Electroencephalography (EEG) or Local Field Potentials (LFP) represent 
        microvolt ($\mu\text{{V}}$) level fluctuations driven by synchronous post-synaptic activity in neuronal populations.
        
        #### 1. Standard EEG Spectral Bands
        - **Delta ($\delta$: 0.5 – 4 Hz)**: Dominant during deep non-REM sleep; pathologically elevated in cerebral lesions.
        - **Theta ($\theta$: 4 – 8 Hz)**: Associated with drowsiness, memory encoding, and deep meditation.
        - **Alpha ($\alpha$: 8 – 13 Hz)**: Relaxed wakefulness with closed eyes (occipital visual cortex inhibition).
        - **Beta ($\beta$: 13 – 30 Hz)**: Active focus, sensory processing, and motor planning (sensorimotor cortex).
        - **Gamma ($\gamma$: 30 – 100+ Hz)**: Complex cognitive binding, cross-modal integration, and fast local network spikes.
        
        #### 2. Welch's Periodogram Power Spectral Density (PSD)
        Welch's method divides a continuous signal $x[n]$ into $K$ overlapping segments of length $L$, applies a Hann window $w[n]$, and computes average periodograms:
        $$P_{{xx}}(f) = \frac{{1}}{{K \cdot U}} \sum_{{k=1}}^{{K}} \left| \sum_{{n=0}}^{{L-1}} x_k[n] w[n] e^{{-j 2 \pi f n}} \right|^2$$
        where $U = \frac{{1}}{{L}} \sum_{{n=0}}^{{L-1}} w^2[n]$ is the window normalization factor.
        
        **Learn More in VIREON Docs**: [NL-001 Fundamental Neuroanatomy & Signal Processing]({DOCS_BASE_URL}/lessons/NL-001/part1_concepts/)
        """)

def render_dbs_education_expander():
    """Renders interactive educational accordion for Deep Brain Stimulation & Safety Limits."""
    with st.expander("ACADEMY: CLOSED-LOOP DBS & CLINICAL SAFETY THRESHOLDS", expanded=False):
        st.markdown(rf"""
        ### Deep Brain Stimulation (DBS) & Tissue Safety Limits
        
        Deep Brain Stimulation delivers high-frequency electrical pulses directly into basal ganglia structures 
        (e.g., Subthalamic Nucleus or Globus Pallidus Internus) to suppress pathological beta oscillations in Parkinson's disease.
        
        #### 1. Shannon Charge Density Equation
        To prevent irreversible local neural tissue damage and electrode dissolution, charge density per phase $D$ must not exceed the Shannon Limit:
        $$\log(D) = k - \log(Q)$$
        where $Q = I \cdot t$ is the phase charge in $\mu\text{{C}}$, $D = Q / A$ is charge density in $\mu\text{{C/cm}}^2$, and $k \approx 1.5$ to $1.8$ for platinum-iridium electrodes.
        
        #### 2. ISO 14708-3 Active Implantable Safety Requirements
        - **Maximum Tissue Heating ($\Delta T$)**: Must not exceed $+1.0^\circ\text{{C}}$ during continuous stimulation.
        - **Direct Current Leakage**: Mandatory hardware blocking capacitors to prevent $DC < 1.0\,\mu\text{{A}}$ electrochemical lysis.
        
        **Learn More in VIREON Docs**: [NL-003 Neurostimulation & Closed-Loop Controls]({DOCS_BASE_URL}/lessons/NL-003/part1_concepts/)
        """)

def render_stride_mitre_atlas_matrix():
    """Renders interactive STRIDE vs MITRE ATLAS threat mapping table."""
    st.markdown("### STRIDE & MITRE ATLAS Neurosecurity Threat Matrix")
    st.caption("Cross-mapping of physical, wireless, and algorithmic threat vectors affecting neural implants and BCI decoders.")
    
    matrix_data = [
        {
            "STRIDE Category": "Spoofing",
            "MITRE ATLAS ID": "AML.T0001",
            "Technique": "Neural Telemetry Session Hijacking",
            "Attack Vector": "BLE GATT Pair Spoofing",
            "Impact": "Unauthorized access to telemetry stream",
            "ISO 14971 Risk": "MEDIUM"
        },
        {
            "STRIDE Category": "Tampering",
            "MITRE ATLAS ID": "AML.T0015",
            "Technique": "Physical Hardware / Signal Injection",
            "Attack Vector": "Gaussian Noise & DC Offset Drift",
            "Impact": "Corrupts feature extraction & classifier input",
            "ISO 14971 Risk": "HIGH"
        },
        {
            "STRIDE Category": "Repudiation",
            "MITRE ATLAS ID": "AML.T0022",
            "Technique": "Log Evasion & Forensic Erasure",
            "Attack Vector": "Audit Log Buffer Overflow",
            "Impact": "Prevents clinical post-incident analysis",
            "ISO 14971 Risk": "MEDIUM"
        },
        {
            "STRIDE Category": "Information Disclosure",
            "MITRE ATLAS ID": "AML.T0024",
            "Technique": "Neural Privacy Eavesdropping",
            "Attack Vector": "Unencrypted Telemetry Sniffing",
            "Impact": "Leaks cognitive state & motor intent",
            "ISO 14971 Risk": "HIGH"
        },
        {
            "STRIDE Category": "Denial of Service",
            "MITRE ATLAS ID": "AML.T0029",
            "Technique": "Neurostimulator Battery Starvation",
            "Attack Vector": "High-Rate Wireless Ping Flood",
            "Impact": "Premature battery depletion, therapy loss",
            "ISO 14971 Risk": "CRITICAL"
        },
        {
            "STRIDE Category": "Elevation of Privilege",
            "MITRE ATLAS ID": "AML.T0038",
            "Technique": "Uncontrolled Pulse Train Injection",
            "Attack Vector": "Over-stimulation Attack",
            "Impact": "Tissue damage, induced seizure",
            "ISO 14971 Risk": "CRITICAL"
        }
    ]
    
    df_matrix = pd.DataFrame(matrix_data)
    st.dataframe(df_matrix, use_container_width=True)
