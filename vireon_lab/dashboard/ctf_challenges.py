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
VIREON Neurosecurity Capture-the-Flag (CTF) Challenge Suite.
Provides hands-on interactive scenarios for identifying, diagnosing, and mitigating
threats against brain-computer interfaces and neurostimulators.
"""

import streamlit as st

def render_ctf_challenge_suite():
    """Renders interactive CTF challenge scenarios in Streamlit."""
    st.markdown("### 🚩 VIREON Neurosecurity CTF & Defense Challenges")
    st.caption("Interactive hands-on scenarios to test your skills in detecting, diagnosing, and mitigating neurotech cyber-physical threats.")
    
    if "ctf_score" not in st.session_state:
        st.session_state.ctf_score = 0
    if "solved_challenges" not in st.session_state:
        st.session_state.solved_challenges = set()

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        st.metric("Total CTF Score", f"{st.session_state.ctf_score} PTS")
    with c2:
        st.metric("Challenges Solved", f"{len(st.session_state.solved_challenges)} / 4")
    with c3:
        if st.button("Reset CTF Progress"):
            st.session_state.ctf_score = 0
            st.session_state.solved_challenges = set()
            st.rerun()

    st.divider()

    # Challenge 1: Stealth Baseline Drift
    with st.expander("🚩 **Challenge 1: Detect Stealthy Baseline Drift (100 PTS)**", expanded=("ch1" not in st.session_state.solved_challenges)):
        st.markdown("""
        **Scenario**: An attacker has injected a low-frequency $0.05\,\text{Hz}$ DC offset drift into electrode **F3**.
        The raw amplitude stays within range, but feature extraction filters are failing.
        
        **Goal**: Identify which DSP metric reveals the stealth drift attack.
        """)
        ans1 = st.radio(
            "Which indicator best isolates the DC drift attack?",
            [
                "A) High Gamma band power (>50 Hz)",
                "B) Very Low Frequency (VLF < 0.5 Hz) spectral accumulation & baseline mean shift",
                "C) Increase in BLE packet notify throughput",
                "D) Drop in battery percentage"
            ],
            key="ctf_q1"
        )
        if st.button("Submit Challenge 1", key="sub_ch1"):
            if "B)" in ans1:
                if "ch1" not in st.session_state.solved_challenges:
                    st.session_state.ctf_score += 100
                    st.session_state.solved_challenges.add("ch1")
                st.success("🎉 **CORRECT!** (+100 PTS) DC offset drift manifests as ultra-low frequency spectral energy accumulation near 0 Hz.")
            else:
                st.error("❌ Incorrect. Hint: Think about what frequency range a slow DC baseline drift occupies.")

    # Challenge 2: Shannon Charge Density Limit
    with st.expander("🚩 **Challenge 2: Clinical Over-Stimulation Mitigation (150 PTS)**", expanded=("ch2" not in st.session_state.solved_challenges)):
        st.markdown("""
        **Scenario**: An unauthorized pulse train injection has raised DBS amplitude to **$8.5\,\text{mA}$** at **$180\,\text{Hz}$**.
        The calculated charge density exceeds the Shannon limit ($4.0\,\mu\text{C/phase}$), threatening local tissue necrosis.
        
        **Goal**: Determine the immediate mitigation action required by ISO 14708-3.
        """)
        ans2 = st.radio(
            "What is the compliant clinical safety action?",
            [
                "A) Increase stimulation frequency to 250 Hz",
                "B) Disconnect battery charging coil",
                "C) Trigger automatic charge-density clamp / hardware safety interlock to suspend stimulation",
                "D) Ignore alert until next scheduled clinic visit"
            ],
            key="ctf_q2"
        )
        if st.button("Submit Challenge 2", key="sub_ch2"):
            if "C)" in ans2:
                if "ch2" not in st.session_state.solved_challenges:
                    st.session_state.ctf_score += 150
                    st.session_state.solved_challenges.add("ch2")
                st.success("🎉 **CORRECT!** (+150 PTS) ISO 14708-3 requires immediate hardware interlock trip when Shannon safety limits are violated.")
            else:
                st.error("❌ Incorrect. Hint: Safety interlocks must act autonomously without clinical delay.")

    # Challenge 3: Session Replay Attack Detection
    with st.expander("🚩 **Challenge 3: Spotting Neural Session Replay (150 PTS)**", expanded=("ch3" not in st.session_state.solved_challenges)):
        st.markdown("""
        **Scenario**: An adversary intercepts a 10-second segment of motor imagery telemetry and replays it over BLE to spoof user intent.
        
        **Goal**: How does the VIREON Ring-Buffer engine detect session replay attacks?
        """)
        ans3 = st.radio(
            "Select the primary replay detection mechanism:",
            [
                "A) Monotonic cryptographic sequence counter & phase continuity verification",
                "B) Checking electrode impedance",
                "C) Measuring room temperature",
                "D) Visual inspection of the waveform color"
            ],
            key="ctf_q3"
        )
        if st.button("Submit Challenge 3", key="sub_ch3"):
            if "A)" in ans3:
                if "ch3" not in st.session_state.solved_challenges:
                    st.session_state.ctf_score += 150
                    st.session_state.solved_challenges.add("ch3")
                st.success("🎉 **CORRECT!** (+150 PTS) Sequence counters combined with phase continuity checks prevent stale replay payloads.")
            else:
                st.error("❌ Incorrect. Hint: Cryptographic freshness requires sequence numbering.")

    # Challenge 4: Adversarial FGSM Evasion
    with st.expander("🚩 **Challenge 4: Adversarial Machine Learning Defense (200 PTS)**", expanded=("ch4" not in st.session_state.solved_challenges)):
        st.markdown("""
        **Scenario**: An FGSM attack adds subtle perturbation ($\varepsilon = 0.15$) to EEG spectral power features, causing a motor imagery classifier to drop from 98% to 25% accuracy.
        
        **Goal**: What defense strategy hardens BCI decoders against adversarial gradient perturbations?
        """)
        ans4 = st.radio(
            "Which defense technique provides robust protection?",
            [
                "A) Increasing canvas render height",
                "B) Adversarial training with spatial covariance filtering (CSP) & gradient clipping",
                "C) Using a longer USB cable",
                "D) Turning off the computer monitor"
            ],
            key="ctf_q4"
        )
        if st.button("Submit Challenge 4", key="sub_ch4"):
            if "B)" in ans4:
                if "ch4" not in st.session_state.solved_challenges:
                    st.session_state.ctf_score += 200
                    st.session_state.solved_challenges.add("ch4")
                st.success("🎉 **CORRECT!** (+200 PTS) Adversarial training combined with Common Spatial Pattern (CSP) filtering neutralizes gradient perturbations!")
            else:
                st.error("❌ Incorrect. Hint: Robust ML requires multi-resolution spatial filtering and adversarial retraining.")
