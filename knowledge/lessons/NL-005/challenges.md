# NL-005 Challenges

## CTF-009: Controller Parameter Extraction via Stimulation Side-Channels
**Difficulty:** Advanced
**Type:** CTF
**Time Estimate:** 8-12 hours

**Description:** Closed-loop neurostimulators continuously adjust stimulation parameters based on sensed biomarkers. These output patterns can leak information about the internal controller gains, thresholds, and adaptation logic. In this challenge, you are provided with time-series recordings of stimulation amplitude, frequency, and pulse width from an adaptive DBS system operating in closed-loop mode. Your task is to perform system identification on the output side-channel to reverse-engineer the PID controller parameters and the biomarker threshold values embedded in the implant.

**Objectives:**
- Capture and preprocess stimulation pattern time-series data from the provided pcap recordings
- Apply system identification techniques (least-squares, subspace methods) to estimate controller transfer function coefficients
- Recover the exact PID gain values (Kp, Ki, Kd) and the LFP beta-band threshold used by the adaptive controller

**Deliverables:** A written report including the estimated controller parameters with confidence intervals, the methodology used for system identification, and a Python script that reproduces the extraction pipeline.

**Hints:**
1. The stimulation updates occur at a fixed control loop rate—start by identifying this period from the timestamp differences.
2. Consider that the controller output (stimulation change) is proportional to the error signal; use cross-correlation between input perturbations and output responses.
3. The implant uses a discrete-time PID implementation with anti-windup; model the output saturation limits before fitting the linear model.

**Resources:** Section 2.3, Ogata (Modern Control Engineering) Ch. 7-8

---

## CTF-010: Evasive Adversarial Sensor Signal Generation
**Difficulty:** Advanced
**Type:** CTF
**Time Estimate:** 8-12 hours

**Description:** Closed-loop neurostimulators employ rate-of-change (RoC) detectors to reject spurious sensor readings caused by motion artifacts or electromagnetic interference. However, a sophisticated adversary can craft sensor signals that remain within the RoC bounds while systematically biasing the controller toward harmful states. This challenge provides a simulated adaptive DBS controller with a known RoC detection threshold. You must design an adversarial LFP-like signal that passes all plausibility checks yet maximizes the steady-state control error, driving stimulation to clinically dangerous levels.

**Objectives:**
- Analyze the rate-of-change detection algorithm and identify the exact threshold and windowing parameters
- Formulate the adversarial signal generation as a constrained optimization problem (maximize error subject to RoC constraints)
- Generate a synthetic sensor trace that evades detection for at least 60 seconds of simulated time while achieving >40% control deviation

**Deliverables:** A synthetic sensor signal file (CSV), the optimization script used to generate it, and a brief analysis explaining why the signal evades detection.

**Hints:**
1. The RoC detector operates on a sliding window—exploit the boundary between consecutive windows to inject abrupt changes that are individually within limits.
2. Use gradient-based optimization (e.g., projected gradient descent) where the projection step enforces the per-sample rate constraint.
3. Adding low-amplitude high-frequency noise can mask the adversarial bias in spectral checks that the controller may also perform.

**Resources:** Section 3.2, Franklin Powell (Feedback Control of Dynamic Systems) Ch. 4

---

## VAL-009: Real-Time Stability Margin Estimator for Closed-Loop Monitoring
**Difficulty:** Advanced
**Type:** VAL
**Time Estimate:** 8-12 hours

**Description:** Safety monitors for closed-loop neurostimulators must detect impending instability before the system diverges. Traditional approaches trigger alarms only after outputs exceed fixed thresholds, which may be too late for adaptive systems with complex dynamics. In this challenge, you will implement a real-time stability margin estimator that continuously computes the gain margin and phase margin of the closed-loop transfer function from online input-output data. The estimator must handle noisy biomedical signals, operate within the computational constraints of an embedded processor, and raise warnings when margins drop below clinically defined safety envelopes.

**Objectives:**
- Implement a recursive least-squares (RLS) or extended Kalman filter based online system identification module
- Compute gain margin and phase margin estimates from the identified transfer function at each control cycle
- Integrate a safety state machine that transitions between NORMAL, WARNING, and CRITICAL based on margin thresholds

**Deliverables:** A Python module implementing the stability margin estimator, unit tests with simulated stable and unstable closed-loop scenarios, and a performance benchmark showing execution time per control cycle.

**Hints:**
1. Use a forgetting factor in your RLS implementation to track time-varying dynamics without accumulating stale data.
2. The gain margin can be estimated by finding the frequency where the phase crosses -180 degrees in the identified frequency response.
3. Pre-compute a lookup table for the arctangent function to reduce computational cost on embedded platforms.

**Resources:** Section 4.1, Nise (Control Systems Engineering) Ch. 10

---

## VAL-010: Cross-Channel Consistency Checks for Bilateral DBS Systems
**Difficulty:** Advanced
**Type:** VAL
**Time Estimate:** 8-12 hours

**Description:** Bilateral deep brain stimulation systems independently control stimulation on the left and right hemispheres, creating two parallel closed loops. Under normal physiology, bilateral beta-band LFP activity exhibits strong inter-hemispheric coherence. An attacker compromising a single channel can break this coherence without triggering unilateral anomaly detectors. This challenge requires you to design and implement cross-channel consistency checks that detect when one channel's sensor or controller behavior diverges from the expected bilateral correlation structure, providing defense-in-depth against asymmetric attacks.

**Objectives:**
- Implement real-time coherence and cross-correlation computation between bilateral LFP channels
- Design a statistical test (e.g., Granger causality, mutual information) to detect unilateral anomalies in the sensor-controller chain
- Create a fusion logic that combines unilateral and cross-channel anomaly scores into a single integrity metric

**Deliverables:** A Python implementation of the cross-channel consistency monitor, test cases demonstrating detection of single-channel attacks, and a comparison report against unilateral-only monitoring.

**Hints:**
1. Use Welch's method for estimating the cross-spectral density—window lengths of 1-2 seconds provide a good trade-off between resolution and latency.
2. Bilateral coherence is frequency-dependent; focus your consistency check on the beta band (13-30 Hz) where adaptive DBS algorithms operate.
3. A sudden drop in coherence combined with normal unilateral statistics is the strongest indicator of a compromised channel.

**Resources:** Section 4.3, Gilron et al. 2021 (Multi-Center Adaptive DBS)

---

## RES-009: Distance Bounding Protocol for Implantable Closed-Loop Devices
**Difficulty:** Advanced
**Type:** RES
**Time Estimate:** 8-12 hours

**Description:** Relay attacks pose a severe threat to implantable closed-loop neurostimulators, where an adversary could forward commands between a legitimate programmer and the implant to alter therapy parameters from a distance. Distance bounding protocols allow a verifier to establish an upper bound on the physical distance to a prover by measuring round-trip time of challenge-response exchanges. However, implantable devices face unique constraints: ultra-low power budgets, strict timing requirements, and variable propagation delays through body tissue. This challenge asks you to design a distance bounding protocol tailored to implantable neurostimulators that can reliably detect relay attacks within 10 cm resolution.

**Objectives:**
- Design a rapid challenge-response protocol with single-bit exchanges minimizing computation at the implant side
- Model the timing uncertainty introduced by body tissue propagation (2-10 ns variability) and processing jitter
- Analyze the protocol's resistance to mafia, terrorist, and distance fraud attacks under the implantable threat model

**Deliverables:** A protocol specification document, a formal security analysis using Dolev-Yao or similar model, and a simulation evaluating detection probability versus distance under realistic channel conditions.

**Hints:**
1. Use pre-shared keys for lightweight MAC computation on single-bit challenges rather than public-key operations.
2. The speed of electromagnetic signals through body tissue is approximately 0.5c—account for this in your distance calculations.
3. Consider using multiple rapid rounds with majority voting to reduce the probability of a lucky relay attack succeeding.

**Resources:** Section 5.2, IEC 62443-3-3 (System Security Requirements)

---

## RES-010: Post-Quantum Secure Parameter Authentication for Closed-Loop Neurostimulators
**Difficulty:** Advanced
**Type:** RES
**Time Estimate:** 8-12 hours

**Description:** Current neurostimulator programming protocols rely on cryptographic primitives (AES, ECC) that are vulnerable to future quantum computers via Shor's algorithm. While implantable devices have a service life of 5-25 years, the timeline for practical quantum computers is converging with this horizon, creating a harvest-now-decrypt-later threat for recorded parameter exchanges. This challenge requires you to propose a post-quantum secure authentication and key establishment scheme suitable for the extreme resource constraints of an implantable neurostimulator, considering latency, energy, and memory limitations inherent to the platform.

**Objectives:**
- Evaluate NIST post-quantum candidates (CRYSTALS-Kyber, CRYSTALS-Dilithium, SPHINCS+) for suitability in implantable contexts
- Design a hybrid classical-post-quantum protocol that maintains backward compatibility with existing programmer devices
- Quantify the computational and energy overhead of the proposed scheme compared to current ECC-based authentication

**Deliverables:** A protocol design document with message flow diagrams, a performance analysis comparing overhead to baseline ECC, and a recommendation on the most suitable post-quantum primitive for implantable use.

**Hints:**
1. SPHINCS+ has the largest signatures but is hash-based and requires no special arithmetic hardware—consider whether the implant has a hardware crypto accelerator.
2. A hybrid approach can use ECC for session establishment and a post-quantum KEM for long-term key agreement, balancing latency and future-proofing.
3. The IEEE 11073 SDC profile already defines a certificate-based trust model that can be extended with post-quantum certificates.

**Resources:** Section 5.4, NIST PQC Standardization Process Documentation

---

## BENCH-009: Protocol-in-the-Loop Fuzzing Framework for Closed-Loop Neurostimulators
**Difficulty:** Advanced
**Type:** BENCH
**Time Estimate:** 8-12 hours

**Description:** Traditional protocol fuzzing (as covered in NL-004) tests communication layers in isolation, missing the critical interaction between malformed protocol messages and the closed-loop control response. A command that appears valid at the protocol layer may trigger dangerous control behavior when the stimulation parameter change is processed by the adaptive controller. This challenge requires you to build a protocol-in-the-loop fuzzing framework that combines NL-004 protocol fuzzing techniques with a closed-loop simulation of the NL-005 controller, enabling discovery of safety violations that only manifest through the interaction of both layers.

**Objectives:**
- Integrate a protocol fuzzer with a real-time closed-loop neurostimulator simulation (using the VIREON toolchain)
- Define feedback-guided mutation strategies that prioritize inputs causing large control deviations or stability margin reductions
- Implement coverage metrics that combine protocol state coverage with control-theoretic state-space coverage

**Deliverables:** The fuzzing framework source code, a configuration file defining the fuzzing campaign, and a results report documenting any discovered safety violations with severity classifications.

**Hints:**
1. Use the python-control library to simulate the plant (neural system) and controller in real-time while feeding mutated protocol messages.
2. Guide the fuzzer using a fitness function based on the integral of absolute control error—inputs that maximize this value are most interesting.
3. Record full traces of protocol state and control state for each input so that post-hoc root cause analysis can determine whether the violation originated at the protocol or control layer.

**Resources:** Section 6.1, VIREON Toolchain Documentation

---

## BENCH-010: Energy Side-Channel Analysis Pipeline for Closed-Loop Neurostimulators
**Difficulty:** Advanced
**Type:** BENCH
**Time Estimate:** 8-12 hours

**Description:** The power consumption profile of a closed-loop neurostimulator varies with the stimulation parameters being delivered, which are in turn determined by the sensed biomarker values and the controller's response. An attacker with physical proximity can measure these energy fluctuations using electromagnetic probes, potentially reconstructing the patient's neural state, the controller's internal state, or the stimulation parameters being applied. This challenge requires you to develop an end-to-end energy side-channel analysis pipeline that processes raw electromagnetic emission captures, correlates them with stimulation events, and extracts sensitive closed-loop state information.

**Objectives:**
- Build a signal processing pipeline that captures and synchronizes electromagnetic probe data with known stimulation timing references
- Implement correlation power analysis (CPA) and differential power analysis (DPA) techniques adapted for neurostimulator energy profiles
- Evaluate the information leakage by attempting to reconstruct controller state variables (error signal, integral term, derivative term) from the side-channel traces

**Deliverables:** The analysis pipeline source code, sample output showing reconstructed controller states versus ground truth, and a mitigation recommendations report.

**Hints:**
1. Use GNU Radio with a HackRF SDR to capture the electromagnetic emissions—configure it for the expected stimulation pulse repetition rate.
2. Align your traces to the stimulation pulse edges using cross-correlation before performing statistical analysis.
3. The integral term of a PID controller accumulates over time, making it the most extractable state variable via long-term averaging of power traces.

**Resources:** Section 6.3, GNU Radio Documentation; HackRF Wiki
