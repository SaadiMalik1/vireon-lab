# NL-005: Closed-Loop System Security for Neurostimulators
# Part 3: Synthesis (Sections 29-42)

---

## Section 29: CL Benchmark Framework — CL-001 through CL-008

### 29.1 Benchmark Design Philosophy

The CL (Closed-Loop) benchmarks extend the VIREON benchmark framework to the closed-loop domain. Unlike the WP benchmarks (NL-004) that test protocol-level security in isolation, the CL benchmarks test security properties that emerge from the interaction of sensing, processing, control, and actuation in a dynamic feedback system. Each CL benchmark specifies a threat scenario, the system configuration under test, the attack injection method, the observable outcomes, and the pass/fail criteria.

The CL benchmarks are designed to be implemented in the Lab 002 simulator (loop_attacks.py) and verified against the Lab 001 closed-loop simulator (closed_loop_simulator.py). They follow the same scoring structure as WP benchmarks: 10 tests per benchmark, each worth 10 points, for a maximum of 80 points across the full suite. A system passes a benchmark if it scores >= 8/10.

### 29.2 CL-001: Sensor Spoofing Detection

**Threat:** An attacker injects false neural data that causes the controller to make incorrect stimulation decisions.

**Test configuration:** The closed-loop system runs in normal mode. The attacker injects a beta-power offset (constant, +5 dB, +10 dB, +15 dB) starting at cycle 200 and persisting for 100 cycles. Ten tests vary the injection magnitude, onset speed (instantaneous vs. gradual), and spectral shape (narrowband vs. broadband).

**Pass criteria:** (a) The safety monitor detects the injection within 20 cycles of onset, (b) the system transitions to a safe mode (open-loop fallback or stimulation reduction), (c) the forensic log records the anomaly details (detection time, injection magnitude estimate).

**Scoring:** 2 points per test: 1 for detection within time window, 1 for correct response action. Maximum 20/20 for this benchmark. Scaled to 10 points for the overall CL score.

### 29.3 CL-002: Adversarial Perturbation Resilience

**Threat:** An attacker injects a carefully crafted perturbation optimized to shift the feature value while evading simple threshold-based detection.

**Test configuration:** The attacker computes a perturbation using a gradient-based optimization (Section 20.2) that maximizes feature shift while keeping the raw-signal perturbation magnitude below a threshold (epsilon = 0.1, 0.2, 0.5, 1.0 times the natural signal standard deviation). Ten tests vary the perturbation budget (epsilon) and the optimization objective (positive shift, negative shift, oscillatory).

**Pass criteria:** (a) The system detects the perturbation with higher probability than random guessing (detection rate > 50% across 10 tests), (b) the closed-loop output deviation (stimulation error relative to no-attack baseline) remains below 2x the natural variability.

### 29.4 CL-003: Controller Parameter Integrity

**Threat:** An attacker modifies the PI controller gains (Kp, Ki) to destabilize the closed-loop system or alter its behavior.

**Test configuration:** The attacker modifies Kp (x2, x5, x10 increase) and Ki (x2, x5, x10 increase) individually and in combination. Ten tests cover different parameter modification patterns, including slow (gradual over 100 cycles) and fast (instantaneous) modifications.

**Pass criteria:** (a) The system detects the parameter modification within 10 cycles, (b) the system reverts to the last authorized parameter set, (c) if the modified parameters would cause instability, the system switches to safe mode before instability manifests.

### 29.5 CL-004: Setpoint Integrity

**Threat:** An attacker modifies the therapeutic setpoint to an incorrect value, causing the controller to pursue the wrong objective.

**Test configuration:** The attacker shifts the setpoint by -5 dB, -10 dB, +5 dB, +10 dB, and sets it equal to the current beta power (tracking attack). Ten tests vary the setpoint modification magnitude and speed.

**Pass criteria:** (a) The system detects the setpoint modification within 20 cycles, (b) the system reverts to the authorized setpoint, (c) the forensic log records the unauthorized setpoint change.

### 29.6 CL-005: Energy Depletion Detection

**Threat:** An attacker increases the device's energy consumption to drain the battery prematurely.

**Test configuration:** The attacker spoofs sensor data to force maximum stimulation (energy multiplier 5x, 10x), triggers excessive wireless communication (20 packets/sec, 50 packets/sec), and combines both. Ten tests vary the attack type and duration.

**Pass criteria:** (a) The energy monitor detects abnormal consumption rate (> 3x baseline) within 50 cycles, (b) the system flags a projected battery life below the safety threshold, (c) the system reduces non-essential energy consumption (e.g., reduces telemetry rate).

### 29.7 CL-006: Safety Monitor Evasion Detection

**Threat:** A sophisticated attacker combines multiple attack techniques to evade the safety monitor while performing a destabilizing attack.

**Test configuration:** The attacker performs a composite attack: (a) timing desynchronization + sensor spoofing, (b) threshold elevation + gain manipulation, (c) alarm fatigue + setpoint modification. Ten tests vary the evasion technique and the primary attack type.

**Pass criteria:** (a) The system detects the primary attack despite the evasion technique, or (b) the system detects the evasion technique itself, or (c) the multi-metric correlation identifies inconsistencies that indicate evasion.

### 29.8 CL-007: Protocol-Loop Interaction Security

**Threat:** An attacker exploits the wireless protocol to affect the closed-loop system's behavior through unauthorized parameter changes or communication disruption.

**Test configuration:** The attacker performs: (a) unauthorized parameter change via replayed command, (b) communication-induced jitter during closed-loop operation, (c) telemetry injection to mislead clinician. Ten tests vary the protocol attack type and its interaction with the control loop.

**Pass criteria:** (a) Protocol-level attacks do not affect the closed-loop operation (the control loop continues with authorized parameters), (b) communication disruption does not cause the control loop to destabilize (the loop operates independently of the wireless link), (c) telemetry anomalies are flagged on the clinician programmer.

### 29.9 CL-008: Forensic Analysis Capability

**Threat:** After an attack (or suspected attack), the system must provide sufficient forensic data to determine what happened.

**Test configuration:** After each of the previous attack scenarios (CL-001 through CL-007), the system produces a forensic report. Ten tests evaluate the quality of the forensic data for different attack types.

**Pass criteria:** (a) The forensic report correctly identifies the attack type (at least the category: sensor, controller, setpoint, timing, energy), (b) the forensic report provides a timeline of attack events with cycle-level resolution, (c) the forensic data is cryptographically integrity-protected (cannot be modified after generation).

---

## Section 30: Digital Twin Integration

### 30.1 Digital Twin Architecture for Closed-Loop

The VIREON digital twin for closed-loop neurostimulation is a high-fidelity simulation model that replicates the complete closed-loop system: neural signal generation, sensing, processing, control, actuation, and safety monitoring. The digital twin serves three purposes in the VIREON ecosystem: (a) pre-deployment validation — testing the closed-loop system's behavior under a wide range of conditions before clinical use, (b) attack simulation — evaluating the system's response to security threats in a safe environment, (c) anomaly diagnosis — comparing the device's actual behavior to the twin's predicted behavior to detect anomalies.

The digital twin consists of five sub-models, each corresponding to a functional block from Section 3.1:

**Neural signal model (Section 4):** Generates realistic beta-band LFP signals with natural variability, stimulation response dynamics, and configurable anomaly injection. The model parameters (baseline beta power, variability, response time constant, stimulation coupling) are patient-specific and calibrated from clinical data.

**Sensing model:** Simulates the electrode-tissue interface, amplifier noise, ADC quantization, and blanking period effects. Includes configurable injection capability for testing sensor spoofing detection.

**Processing model:** Implements the DSP pipeline (bandpass filter, windowed spectral estimation) with configurable parameters. Supports both the primary pipeline and a simplified secondary pipeline for redundancy analysis.

**Controller model:** Implements the PI controller with configurable parameters, anti-windup, rate limiting, and output clamping. Supports parameter modification for testing CL-003 and CL-004.

**Monitor model:** Implements the safety monitor with configurable thresholds, detection algorithms, and response actions. Supports threshold elevation for testing CL-006.

### 30.2 Model Fidelity Levels

VIREON defines three fidelity levels for the digital twin:

**Fidelity 1 (Functional):** Models the system's input-output behavior without internal state. Suitable for rapid prototyping and initial security screening. Does not capture timing-sensitive effects.

**Fidelity 2 (Behavioral):** Models internal state and timing with moderate accuracy. Suitable for CL benchmark testing and attack simulation. Captures the essential dynamics but may simplify non-critical components.

**Fidelity 3 (Cycle-Accurate):** Models every computation and state transition at the control cycle level. Suitable for formal verification integration and detailed forensic analysis. Computationally expensive but provides the highest confidence.

The Lab 001 simulator operates at Fidelity 2 — it models the essential closed-loop dynamics with cycle-level timing but abstracts some implementation details (e.g., fixed-point arithmetic effects, RTOS scheduling).

### 30.3 Twin-Device Divergence Monitoring

In deployed systems, the digital twin runs on the clinician programmer (or cloud server) in parallel with the actual device. The twin receives the same parameter updates and telemetry data, and it predicts the device's behavior. Divergence between the twin's prediction and the device's actual behavior indicates a potential anomaly — either a model inaccuracy (which should be corrected by recalibration) or a security event (which should be investigated).

VIREON defines the divergence metric as the normalized difference between predicted and actual stimulation output, integrated over a sliding window. The divergence threshold is calibrated to the model's expected prediction error under normal operation. A divergence exceeding 3 sigma (covering 99.7% of normal variability) is flagged as anomalous.

---

## Section 31: VIREON Validation Framework Mapping

### 31.1 Validation Points for Closed-Loop Security

The VIREON validation framework defines specific validation points (VPs) for closed-loop neurostimulator security. Each VP specifies what is checked, how it is checked, and the pass/fail criteria.

| VP ID | Validation Point | Check Method | Pass Criteria |
|---|---|---|---|
| VP-CL-01 | Feature value range | Per-cycle range check | beta_power in [min, max] physiologic range |
| VP-CL-02 | Output rate of change | Per-cycle derivative check | d(stim)/dt <= rate_limit |
| VP-CL-03 | Output absolute limits | Per-cycle clamp check | stim in [u_min, u_max] |
| VP-CL-04 | Controller parameter integrity | CRC/Hash verification | Parameter hash matches authorized value |
| VP-CL-05 | Setpoint integrity | Authenticated source check | Setpoint changed only via authenticated command |
| VP-CL-06 | Stability indicator | Multi-cycle oscillation detection | ZCR < threshold, autocorrelation < threshold |
| VP-CL-07 | Sensor anomaly | Statistical consistency check | Signal statistics within physiologic bounds |
| VP-CL-08 | Timing consistency | Cycle time measurement | Cycle time within +/- 1 ms of nominal |
| VP-CL-09 | Energy consumption | Energy rate monitoring | Power < 3x baseline, projected life > 24h |
| VP-CL-10 | Monitor response time | Alarm latency measurement | Monitor responds within 10 cycles of anomaly |

### 31.2 Integration with Previous Module VPs

The closed-loop VPs integrate with VPs from previous modules: VP-CL-01 and VP-CL-07 depend on the DSP pipeline VPs from NL-002, VP-CL-04 and VP-CL-05 depend on the firmware VPs from NL-003, VP-CL-08 depends on the RTOS timing VPs from NL-003, and the wireless-related VPs (VP-CL-05 authenticated commands) depend on the protocol VPs from NL-004. This cross-module dependency chain is why VIREON validation must consider the complete system, not just individual modules.

---

## Section 32: Responsiveness vs Security Tension

### 32.1 The Fundamental Trade-off

Closed-loop neurostimulation faces a fundamental tension between responsiveness (the ability to adapt quickly to genuine clinical changes) and security (the ability to detect and respond to attacks). A highly responsive system adapts stimulation rapidly when the patient's neural state changes, providing optimal therapy. But the same rapid adaptation makes the system vulnerable to attacks that exploit the fast response — a spoofed signal that changes rapidly will be followed by the controller before the monitor can detect the spoofing.

Conversely, a highly secure system with extensive validation on every control cycle is slow to respond because the validation adds latency. If the validation takes 5 ms out of a 10 ms cycle, the effective control rate drops from 100 Hz to 67 Hz (validation is parallelized but still adds latency to the feedback path). The reduced control rate degrades therapeutic performance, especially for rapidly changing neural dynamics.

### 32.2 Quantifying the Trade-off

The trade-off can be quantified using the concept of "security overhead" — the fraction of the control cycle budget consumed by security checks. If the total cycle budget is T = 10 ms, and security checks consume T_security, the effective cycle time is T + T_security (if checks are sequential) or max(T_processing, T_security) (if checks are parallel). The security overhead ratio is T_security / (T + T_security).

For a system with T_security = 1 ms (lightweight checks): overhead = 9%, phase margin loss = approximately 3 degrees. For T_security = 5 ms (comprehensive checks): overhead = 33%, phase margin loss = approximately 15 degrees. The design challenge is to achieve adequate security within a security overhead budget of 10-20%.

### 32.3 Architectural Solutions

Several architectural approaches can mitigate the responsiveness-security tension:

**Asymmetric monitoring:** The control path operates at full speed with minimal validation (per-cycle range checks only). The safety monitor operates on a longer time window (every 10th cycle) but with comprehensive checks (stability analysis, statistical anomaly detection). This provides fast response for normal operation with comprehensive security coverage for abnormal situations.

**Adaptive security level:** The system dynamically adjusts its security level based on the perceived threat level. During normal operation (low threat), security checks are minimal for maximum responsiveness. When an anomaly is detected (elevated threat), security checks are increased at the cost of reduced responsiveness. This is analogous to the "combat mode" in military systems.

**Hardware acceleration:** Security-critical checks (CRC computation, range checking, NaN detection) are implemented in hardware (FPGA or dedicated logic) that operates in parallel with the software control path. This provides comprehensive checking with zero software overhead, at the cost of additional hardware complexity.

---

## Section 33: Multi-Objective Optimization for Closed-Loop Security

### 33.1 Competing Objectives

Designing a secure closed-loop neurostimulation system requires optimizing for multiple competing objectives: therapeutic efficacy (how well the system controls symptoms), safety (how well the system avoids harm), security (how well the system resists attacks), energy efficiency (how long the battery lasts), and computational efficiency (whether the system fits within the hardware constraints).

These objectives are often in conflict. Maximum security (comprehensive checks, independent monitoring, formal verification) requires more computation and energy. Maximum efficacy (fast response, aggressive adaptation) reduces the time available for security checks. Maximum energy efficiency (duty cycling, reduced sampling rate) degrades both efficacy and security.

### 33.2 Pareto-Optimal Design Space

The design space is explored using Pareto optimization: finding designs where no objective can be improved without degrading another. The Pareto frontier defines the set of optimal trade-offs. The designer (or the automated design tool) selects a specific point on the frontier based on clinical priorities.

For VIREON, the primary trade-off is between security (CL benchmark score) and efficacy (control performance metric, e.g., mean squared error of beta power tracking). The Pareto frontier typically shows diminishing returns: the first 20% of security investment (per-cycle range checks) achieves 80% of the maximum security benefit, while the last 20% (formal verification, independent sensing) achieves only 5% additional security benefit but significantly increases cost and complexity.

### 33.3 VIREON Design Space Exploration

The VIREON SDK provides tools for exploring the design space: the digital twin (Section 30) can simulate different configurations, the benchmark framework (CL-001 through CL-008) can evaluate each configuration's security, and the optimization module can search the parameter space for Pareto-optimal designs. The designer specifies constraints (maximum energy budget, minimum efficacy, minimum security score) and the optimizer finds configurations that satisfy all constraints.

---

## Section 34: Case Study — Closed-Loop DBS for Parkinson's Disease

### 34.1 Clinical Context

Parkinson's disease (PD) is a neurodegenerative disorder characterized by the loss of dopaminergic neurons in the substantia nigra, leading to excessive beta-band oscillations (13-30 Hz) in the subthalamic nucleus (STN). Conventional DBS delivers continuous high-frequency stimulation (130 Hz) to the STN, which suppresses beta oscillations and improves motor symptoms. Closed-loop DBS senses beta power in real time and adjusts stimulation amplitude to maintain beta suppression while minimizing total stimulation delivered.

The clinical benefit of closed-loop over open-loop DBS has been demonstrated in multiple studies. The MEDIC (Mechanisms of Deep Brain Stimulation) study at the University of Oxford showed that adaptive DBS reduced total stimulation energy by 40-60% compared to continuous DBS while maintaining equivalent or superior symptom control. A multi-center study (Gilron et al., 2021) confirmed these findings across 12 centers.

### 34.2 Security Analysis

Applying the framework from this module to a representative closed-loop DBS system for PD:

**Most likely attack:** Sensor spoofing (CL-001) — an attacker with physical proximity can inject EM signals at beta frequencies to cause the controller to overstimulate. The attack requires a coil or antenna within 1-10 cm of the patient's head, sustained for at least 500 ms. Detection is challenging because the injected signal is in the same frequency band as genuine beta.

**Highest-impact attack:** Safety monitor evasion combined with controller parameter manipulation (CL-006 + CL-003) — a sophisticated attacker disables the monitor and sets aggressive controller gains, causing oscillatory instability. The patient experiences rapidly fluctuating stimulation, which is both ineffective and distressing.

**Most stealthy attack:** Setpoint tracking (CL-004) — the attacker dynamically adjusts the setpoint to match the current beta power, creating zero error. The system appears to function normally (no alarms, normal stimulation output) but the controller takes no corrective action. If the patient's natural beta power is high (e.g., during medication wearing off), the lack of stimulation leads to clinical deterioration.

### 34.3 Lessons Learned

This case study demonstrates that: (a) the most dangerous attacks are not the most technically sophisticated — sensor spoofing requires only a signal generator and a coil, (b) the safety monitor is essential but not sufficient — it must be designed with evasion resistance, (c) the closed-loop system's dependence on the wireless protocol creates a remote attack surface that open-loop systems lack, (d) the clinician is part of the security chain and must be trained to recognize anomalies.

---

## Section 35: Case Study — Responsive Neurostimulation for Epilepsy

### 35.1 Clinical Context

The NeuroPace RNS System is an FDA-approved responsive neurostimulation device for drug-resistant focal epilepsy. It continuously senses electrocorticographic (ECoG) activity from depth or surface electrodes implanted near the epileptogenic zone. When it detects electrographic seizure activity (using a proprietary detection algorithm), it delivers brief stimulation bursts to abort the seizure before it becomes clinical.

The RNS system's control loop is fundamentally different from closed-loop DBS. It is event-driven rather than continuous: the system monitors continuously but only intervenes when a seizure is detected. The "controller" is a binary detector (seizure / no seizure) rather than a continuous PI controller. The "actuation" is a brief stimulation burst (milliseconds) rather than continuous adjustment.

### 35.2 Security Analysis

The event-driven architecture has different security properties than continuous closed-loop control. The attack surface is narrower (the detector is the critical component, not a continuous controller) but the consequences of a missed detection (undetected seizure) or false detection (unnecessary stimulation) are severe.

**Detector spoofing:** An attacker who can inject ECoG patterns that mimic ictal (seizure) activity can trigger unnecessary stimulation. Repeated false triggers deplete battery (energy attack, CL-005) and may cause the clinician to lower the detection sensitivity, making the system less effective for genuine seizures.

**Detector blinding:** An attacker who can suppress the ictal signal (e.g., through EM injection that cancels the seizure pattern via destructive interference) can prevent the system from detecting genuine seizures. This is a denial-of-therapy attack.

**Detection threshold manipulation:** Modifying the seizure detector's sensitivity threshold has asymmetric effects. Increasing the threshold (requiring stronger evidence for detection) reduces false positives but may miss genuine seizures. Decreasing the threshold increases detection sensitivity but increases false positives. An attacker who can modify the threshold can optimize for either false positives (battery drain, alarm fatigue) or false negatives (missed seizures).

### 35.3 Key Differences from DBS

The RNS system's event-driven architecture means that: (a) timing attacks (Section 18) are less relevant because the system does not have a fixed control loop period, (b) stability analysis (Section 21) does not apply because there is no continuous feedback loop, (c) sensor spoofing (Section 15) is the primary attack class, (d) energy attacks (Section 24) are particularly impactful because each stimulation burst consumes a fixed amount of energy regardless of therapeutic value.

---

## Section 36: Case Study — Closed-Loop Spinal Cord Stimulation

### 36.1 Clinical Context

Closed-loop spinal cord stimulation (SCS) for chronic pain senses evoked potentials (EPs) — neural responses to test stimulation pulses — and adjusts stimulation parameters to maintain the EP within a therapeutic window. The system delivers a test pulse every few seconds, measures the neural response, and adjusts stimulation amplitude, frequency, or pulse width to keep the EP at the target level.

The control loop for SCS is much slower than for DBS (seconds vs. milliseconds) because the neural response to SCS develops over a longer timescale. This slower loop is more robust to timing attacks but provides less responsive therapy.

### 36.2 Security Analysis

The SCS closed-loop system shares many attack surfaces with DBS but has unique characteristics:

**Evoked potential spoofing:** The test pulse is a known, brief stimulus, and the EP is a characteristic waveform with specific latency and morphology. Spoofing an EP requires generating a waveform that matches the expected morphology, which is more constrained than spoofing continuous beta oscillations. However, the EP amplitude is small (1-10 uV) and could potentially be masked or augmented by external EM injection.

**Adaptive threshold manipulation:** The SCS controller adjusts the stimulation to maintain the EP at a target level. If the attacker shifts the perceived EP amplitude (through injection or electrode tampering), the controller adjusts stimulation in the wrong direction. Because the loop is slow (seconds per cycle), the attack has more time per cycle to compute the optimal injection.

**Charge balance in SCS:** SCS typically uses higher stimulation amplitudes than DBS (up to 15 mA) and wider pulse widths (up to 1000 us), making charge balance more critical. An attacker who disables charge-balance checking in an SCS system risks causing more severe tissue damage than in DBS due to the higher charge per phase.

---

## Section 37: Open Research Problems

### 37.1 Fundamental Research Questions

1. **Adversarial closed-loop control:** How do we design controllers that are provably robust to adversarial perturbations of their sensing input? Existing robust control theory (H-infinity, mu-synthesis) addresses bounded disturbances but not adversarially-optimized perturbations. Closing this gap requires integrating control theory with adversarial ML.

2. **Imperfect plant models:** All stability guarantees assume a known plant model, but the neural response to stimulation varies across patients, over time, and with medication state. How do we verify closed-loop security when the plant model has bounded but unknown uncertainty?

3. **Multi-agent closed-loop attacks:** If a patient has multiple implanted devices (e.g., DBS and a cardiac pacemaker), can an attack on one device cascade to affect the other through physiological coupling? The security analysis of multi-implant systems is largely unexplored.

4. **Post-quantum closed-loop security:** Future quantum computers may break the cryptographic protocols (NL-004) used for parameter authentication. How do we maintain closed-loop security in a post-quantum world where parameter updates cannot be authenticated?

5. **Formal verification of learning-based controllers:** As closed-loop neurostimulation moves toward adaptive and learning-based controllers (previewed in NL-006), how do we formally verify the safety and security of controllers whose behavior is not fully specified at design time?

### 37.2 Applied Research Directions

6. **In vivo attack experimentation:** Ethical frameworks for testing closed-loop neurostimulator security in animal models. The simulation-based approach (VIREON) is necessary but not sufficient — biological systems may exhibit behaviors not captured by any model.

7. **Standardized security testing:** Development of international standards (analogous to IEC 62443 for industrial control systems) specifically for closed-loop medical device security. Current standards (IEC 60601-1, FDA guidance) address safety but not security of the feedback loop.

8. **Privacy-preserving telemetry:** Closed-loop systems generate continuous neural data that is transmitted for clinician review and research. How do we protect the privacy of this data while enabling its clinical utility? Differential privacy, federated learning, and homomorphic encryption are candidate approaches.

---

## Section 38: Exercises

### 38.1 Analytical Exercises

**E-001:** For a PI-controlled first-order system with K = 1, tau = 200 ms, T = 10 ms, Kp = 0.05, Ki = 0.005, compute the closed-loop poles and verify they are inside the unit circle. Then compute the poles for Kp = 0.5 and determine whether the system is still stable.

**E-002:** A delay attack adds 30 ms to the feedback path. For the system in E-001, compute the phase margin loss and determine whether the system remains stable. If the gain crossover frequency is 0.158 rad/s, how much additional delay can the system tolerate before instability?

**E-003:** An attacker sets the setpoint 10 dB above the current beta power. Model the controller's response over 50 cycles (500 ms) assuming a first-order neural response with tau = 200 ms. What is the maximum stimulation amplitude reached?

**E-004:** Design a sensor spoofing detection algorithm based on the rate-of-change limit. Given that natural beta variability has sigma = 2 dB and the sample period is T = 10 ms, compute the maximum allowable per-cycle change in beta power for a false alarm rate of < 1 per 1000 cycles.

**E-005:** A closed-loop DBS system has a phase margin of 60 degrees and a gain margin of 12 dB. An attacker increases the controller gain by 6 dB and adds 20 ms of delay. Compute the new phase margin and gain margin. Is the system still stable?

### 38.2 Design Exercises

**E-006:** Design a graduated safety monitor response for a closed-loop DBS system. Specify the detection metrics, thresholds, and response actions for each of the five monitor response levels (Section 10.3). Justify your threshold choices based on clinical and security requirements.

**E-007:** Design a cross-channel consistency check for a bilateral STN DBS system. Specify the metric (correlation coefficient, spectral coherence, or other), the threshold, and the response when the check fails. Consider both genuine inter-hemispheric asymmetry and attack scenarios.

**E-008:** Propose an architecture for a closed-loop neurostimulation system that achieves both high responsiveness (control cycle < 10 ms) and high security (all 10 VPs from Section 31.1 pass). Specify the hardware requirements, software architecture, and timing budget.

---

## Section 39: Glossary

| Term | Definition |
|---|---|
| **Adaptive neurostimulation** | Stimulation that automatically adjusts based on sensed neural activity, as opposed to fixed-parameter (open-loop) stimulation |
| **Anti-windup** | Mechanism to prevent the integral term of a PI controller from accumulating error when the actuator is saturated |
| **Beta-band oscillations** | Neural oscillations in the 13-30 Hz frequency range, used as a biomarker for Parkinson's disease bradykinesia and rigidity |
| **Blacking period** | Time window during and after stimulation when the ADC does not sample, preventing stimulation artifact from entering the control loop |
| **BIBO stability** | Bounded-Input Bounded-Output stability — a system is BIBO stable if every bounded input produces a bounded output |
| **Charge balance** | Requirement that the net charge delivered by a stimulation pulse is zero, preventing electrochemical tissue damage |
| **Closed-loop** | Control architecture where the output is continuously measured and fed back to adjust the input, creating a feedback loop |
| **Control cycle** | One complete sense-process-actuate iteration of the closed-loop system, typically 10-100 ms for DBS |
| **Digital twin** | High-fidelity simulation model of the physical system, used for validation, testing, and anomaly detection |
| **Evoked potential** | Neural response elicited by a test stimulus, used as a feedback signal in closed-loop SCS |
| **Feedback bypass** | Attack that disrupts the feedback path, preventing the controller from receiving accurate sensor data |
| **Gain margin** | Factor by which the loop gain can be increased before instability, measured in dB at the phase crossover frequency |
| **Integral windup** | Condition where the integral term of a PI controller accumulates a large value during actuator saturation, causing overshoot |
| **Phase margin** | Additional phase lag required to bring the system to the stability boundary, measured in degrees at the gain crossover frequency |
| **PI controller** | Proportional-Integral controller: u(t) = Kp * e(t) + Ki * integral(e(t)) |
| **Rate limiting** | Restriction on how fast the controller output can change between consecutive control cycles |
| **Safety monitor** | Independent safety mechanism that watches for dangerous conditions and can force the system into a safe state |
| **Setpoint** | Target value for the controlled variable (e.g., target beta power level) that the controller tries to maintain |
| **Subthalamic nucleus (STN)** | Brain structure targeted by DBS for Parkinson's disease; excessive beta oscillations in STN correlate with motor symptoms |
| **Transfer function** | Mathematical representation of a system's input-output relationship in the frequency domain: G(s) = Y(s)/U(s) |

---

## Section 40: Flashcards

**F-025:** What is the fundamental difference between open-loop and closed-loop neurostimulation from a security perspective?
→ Open-loop has a bounded attack surface (parameters are fixed until changed); closed-loop has an unbounded attack surface because the feedback loop can amplify small perturbations into large, self-sustaining effects.

**F-026:** Why is the safety monitor's independence from the control path critical?
→ If the monitor shares the control path, the same attack that compromises the controller can also compromise the monitor, eliminating the defense-in-depth protection. Independence ensures that an attack on one path does not automatically compromise the other.

**F-027:** What is integral windup, and how can an attacker exploit it?
→ Integral windup occurs when the PI integrator accumulates error during actuator saturation. An attacker can exploit it by (1) spoofing extreme sensor data to cause saturation, (2) allowing the integrator to wind up, (3) removing the trigger — the wound-up integrator then causes extended overstimulation.

**F-028:** How does delay affect closed-loop stability?
→ Delay adds phase lag to the loop transfer function, reducing the phase margin. If the phase margin drops below zero, the system becomes oscillatory unstable. The impact is proportional to the delay-to-period ratio at the gain crossover frequency.

**F-029:** What makes sensor spoofing particularly dangerous for closed-loop systems?
→ The controller is designed to trust its sensor input — there is no "expected" neural signal to validate against. Neural signals are inherently variable, making it difficult to distinguish injected signals from genuine neural activity.

**F-030:** Name five attack surfaces specific to closed-loop neurostimulation.
→ Sensing surface (AS-1), Processing surface (AS-2), Controller surface (AS-3), Actuation surface (AS-4), Monitor surface (AS-5).

**F-031:** What is the "responsiveness vs. security" tension in closed-loop design?
→ Fast response requires minimal per-cycle validation; strong security requires comprehensive per-cycle checks. These compete for the same time budget within the control cycle.

**F-032:** How does the event-driven architecture (e.g., NeuroPace RNS) differ from continuous closed-loop in terms of security?
→ Event-driven systems have a narrower attack surface (detector is the critical component, not a continuous controller) but lack continuous feedback, making timing attacks less relevant and sensor spoofing the primary concern.

---

## Section 41: Interview Questions

**IQ-017:** "Explain how a small change in PI controller gain can cause a closed-loop DBS system to become unstable."
→ The PI gains (Kp, Ki) determine the closed-loop pole locations. Increasing the gains shifts the poles toward the unit circle (or beyond it in the z-plane). When poles cross outside the unit circle, the system response grows without bound — in DBS, this means oscillating or diverging stimulation amplitude. The characteristic equation 1 + C(z)G(z)H(z) = 0 defines the pole locations, and the stability boundary in the (Kp, Ki) plane is found by setting poles on the unit circle.

**IQ-018:** "How would you detect a sensor spoofing attack on a closed-loop neurostimulator, given that neural signals are inherently variable?"
→ Multi-metric physiological plausibility checking: (1) rate-of-change limit — genuine beta changes with tau > 50 ms, step changes are impossible, (2) spectral shape consistency — injected tones have different spectral kurtosis than genuine oscillations, (3) cross-channel correlation — injection on one contact is suspicious, (4) high-frequency harmonic content — EM injection produces harmonics that neural oscillations do not.

**IQ-019:** "Design a safety monitor for a closed-loop DBS system. What does it check, and how does it respond?"
→ The monitor checks: stimulation limits (amplitude, frequency, pulse width, charge), loop stability (oscillation detection via zero-crossing rate and autocorrelation), sensor anomalies (clipping, flatline, spectral anomaly), controller anomalies (windup, NaN, rate violation), and timing anomalies (missed cycles, jitter). Response levels: (1) log and continue, (2) increase monitoring, (3) switch to open-loop, (4) reduce stimulation, (5) disable stimulation, (6) emergency shutdown.

**IQ-020:** "What is the fundamental challenge of securing a closed-loop system that does not exist in open-loop systems?"
→ The feedback loop amplifies perturbations. In an open-loop system, an attack's impact is proportional to the attack magnitude. In a closed-loop system, an attack's impact can be disproportionate to the attack magnitude because the loop's dynamics can amplify a small perturbation into a large, sustained effect (instability). Additionally, the feedback loop creates temporal dependencies where the effect of an attack at time t depends on the system state, which was itself affected by previous attacks.

**IQ-021:** "How would you extend the CL benchmark framework to cover a learning-based adaptive controller (previewed in NL-006)?"
→ Learning-based controllers change their behavior over time based on data, so the benchmarks must test: (1) parameter drift — does the controller's behavior diverge from the clinician's intent over time? (2) training data poisoning — can an attacker influence the controller's learning process? (3) model extraction — can an attacker infer the controller's internal model from its behavior? (4) adversarial examples — can crafted inputs cause the learned model to produce unsafe outputs? The formal verification approach (Section 28) becomes much harder because the controller's behavior is not statically specified.

---

## Section 42: Research Questions

**RQ-017:** Prove or disprove: for any stabilizable first-order plant with known bounds on gain and time constant, there exists a PI controller with a fixed gain margin such that no constant-offset sensor spoofing attack can destabilize the closed-loop system without being detected by a rate-of-change monitor.

**RQ-018:** Given a closed-loop DBS system with a PI controller operating at 100 Hz, what is the minimum duration of a sensor spoofing attack that causes clinically significant overstimulation (amplitude > 5 mA for > 1 second), assuming the attacker optimizes the injection signal subject to a power constraint of P_max watts?

**RQ-019:** Design a formal verification framework for closed-loop neurostimulator security that can prove: (a) bounded-input bounded-output stability for all sensor inputs within specified bounds, (b) detection of all destabilizing parameter modifications within N control cycles, (c) energy safety (battery depletion rate bounded by a function of the stimulation parameters). What are the computational complexity bounds of this framework?

**RQ-020:** Characterize the fundamental limits of sensor spoofing detection for closed-loop neurostimulation. Is there a minimum signal-to-noise ratio below which adversarial perturbation is information-theoretically indistinguishable from genuine neural variability? If so, what are the implications for the design of closed-loop attack detection systems?

**RQ-021:** How should the VIREON benchmark framework evolve to address multi-implant closed-loop systems (e.g., a patient with both a DBS device and a responsive neurostimulator)? What new attack classes emerge from inter-device coupling, and how should cross-device security be validated?

**RQ-022:** Investigate the interaction between closed-loop neurostimulation security and patient privacy. Does the continuous neural data generated by closed-loop systems create a "neural fingerprint" that can be used to identify the patient, infer cognitive state, or predict behavior? What privacy-preserving techniques are compatible with the real-time constraints of closed-loop control?

---

## Module Summary

NL-005 has analyzed the security of closed-loop neurostimulation systems across 42 sections spanning foundations, deep analysis, and synthesis. The key takeaways are:

1. Closed-loop systems create a fundamentally new attack surface — the feedback loop itself — that does not exist in open-loop systems.
2. Control theory (transfer functions, stability margins, phase/gain margins) is the mathematical framework for analyzing closed-loop security.
3. Five attack surfaces (sensing, processing, controller, actuation, monitor) and five perturbation classes (sensor, controller, actuator, delay, reference) provide a systematic taxonomy.
4. The safety monitor is the last line of defense but can itself be evaded through sophisticated multi-vector attacks.
5. The CL benchmark framework (CL-001 through CL-008) provides standardized test scenarios for evaluating closed-loop security.
6. The responsiveness-security tension is a fundamental design constraint that requires architectural solutions (asymmetric monitoring, adaptive security levels, hardware acceleration).
7. This module integrates all previous VIREON modules (NL-001 through NL-004) and provides the foundation for NL-006 (adversarial ML) and NL-007 (digital twins).

**Next:** NL-006 — Adversarial Machine Learning in Neurotechnology. This module extends the adversarial perturbation concepts from Section 20 to the full scope of machine learning models used in neurotechnology: neural signal classifiers, BCI decoders, anomaly detectors, and adaptive controllers.
