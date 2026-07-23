# NL-002 Challenges

---

## CTF Challenges

### CTF-003: Filter Parameter Exploitation

**Difficulty:** Medium | **Category:** Filter Security | **Time:** 2-3 hours

**Scenario:** A closed-loop DBS system uses a 4th-order Butterworth bandpass filter (13-30 Hz) for beta-band extraction. The filter is implemented as an IIR filter (butter, not filtfilt). You have access to the filter coefficients.

**Objective:** Find an injection frequency that passes through the filter's transition band with at least 20% of the injection amplitude, while being outside the nominal 13-30 Hz beta band.

**Success Criteria:**
- Identify the -3dB and -20dB points of the filter
- Find a frequency where attenuation < 14 dB (20% passes)
- Demonstrate with a Python script that shows the injection frequency and resulting filter output

**VIREON Relevance:** Directly validates VIREON's filter security analysis capability.

### CTF-004: Artifact Weaponization

**Difficulty:** Hard | **Category:** Artifact Security | **Time:** 3-4 hours

**Scenario:** An EEG system uses amplitude-threshold artifact detection (threshold: 500 uV RMS in 200 ms windows). The system discards data during detected artifacts.

**Objective:** Design an injection signal that:
1. Triggers artifact detection (forces data rejection)
2. But stays below 500 uV RMS in every 200 ms window
3. Successfully causes data loss >50% of the recording duration

**Hint:** The signal must be designed so that the RMS in each window exceeds the threshold while the peak amplitude stays low. This requires understanding the relationship between RMS, peak, and waveform shape.

---

## Validation Challenges

### VAL-003: Processing Pipeline Fidelity

**Difficulty:** Medium | **Category:** Validation | **Time:** 3-4 hours

**Scenario:** VIREON's digital twin must replicate the processing pipeline of a real device. You have two implementations of the same band-power computation: one in Python (Lab 001) and one in C (reference from a device manufacturer's firmware).

**Objective:** Determine if the two implementations produce equivalent results.

**Tasks:**
1. Process a 60-second synthetic EEG signal through both implementations
2. Compare band power time series using: correlation, RMS error, max absolute error
3. Identify the source of any discrepancies (filter coefficient precision, window alignment, etc.)
4. Define quantitative equivalence criteria (e.g., correlation > 0.999, RMS error < 1%)

### VAL-004: False Positive Rate Under Normal Variation

**Difficulty:** Medium | **Category:** Validation | **Time:** 3-4 hours

**Scenario:** Lab 002's attack detector was tested against clean signals and produced false positives. For a safety-critical system, the false positive rate must be <0.1%.

**Objective:** Characterize the false positive rate of each detection method under normal physiological variation.

**Tasks:**
1. Generate 100 clean signals with different random seeds (simulating different subjects/sessions)
2. Run each detection method on each signal (using the signal against itself as "clean" and "test")
3. Measure false positive rate per method
4. Identify which method has the highest false positive rate
5. Propose threshold adjustments to achieve <0.1% FPR

---

## Research Challenges

### RES-003: Compression-Preserving Attack Detection

**Difficulty:** Hard | **Category:** Research | **Time:** 8-12 hours

**Scenario:** Lossy compression removes information, potentially removing attack artifacts. Can we design attack detection methods that are robust to lossy compression?

**Objective:** Design a detection method that maintains >80% detection rate after the signal is compressed at 10:1 ratio.

**Deliverable:** 500-word research proposal.

### RES-004: Cross-Modal Attack Transfer

**Difficulty:** Very Hard | **Category:** Research | **Time:** 10-15 hours

**Scenario:** An attacker develops an adversarial example against an EEG-based BCI classifier. Will the same adversarial perturbation be effective against an ECoG-based classifier?

**Objective:** Analyze whether adversarial examples transfer across neural signal modalities. If so, what properties of the transfer enable it?

**Deliverable:** Experimental analysis with synthetic data, plus a 500-word research proposal.

---

## Benchmark Challenges

### BENCH-003: Multi-Method Detection ROC Curves

**Difficulty:** Medium | **Category:** Benchmark | **Time:** 4-6 hours

**Scenario:** VIREON needs ROC curves for each detection method across a range of attack strengths.

**Objective:** Generate ROC curves for all 4 detection methods.

**Tasks:**
1. For each method, vary the attack strength (e.g., injection amplitude: 1, 5, 10, 20, 50, 100 uV)
2. For each strength, run 50 trials with different random seeds
3. Compute TPR and FPR at each strength
4. Plot ROC curves for each method
5. Compute AUC for each method

### BENCH-004: Processing Latency Benchmark

**Difficulty:** Easy-Medium | **Category:** Benchmark | **Time:** 2-3 hours

**Scenario:** Signal processing adds latency. VIREON needs to characterize this latency for different pipeline configurations.

**Objective:** Measure the processing latency of the full pipeline from Lab 001.

**Tasks:**
1. Time each processing stage independently (filtering, artifact detection, feature extraction)
2. Measure total pipeline latency for different signal lengths (1s, 10s, 60s, 300s)
3. Measure latency per channel for different channel counts (1, 8, 32, 128)
4. Identify the bottleneck stage
5. Report results in a standardized format