# NL-005: Closed-Loop System Security for Neurostimulators
# Part 1: Foundations (Sections 1-14)

---

## Section 1: Closed-Loop Neurostimulation — The Paradigm Shift

### 1.1 From Open-Loop to Closed-Loop

Open-loop neurostimulation delivers therapy according to pre-programmed parameters that remain fixed until a clinician explicitly changes them. A Parkinson's patient receiving conventional DBS might have stimulation set to 3.0 V amplitude, 130 Hz frequency, and 60 us pulse width — parameters that do not change regardless of whether the patient is resting, walking, or experiencing a dyskinesia episode. The clinician adjusts these parameters during periodic office visits based on subjective patient reports and brief clinical observations. This approach treats neural pathology as static, when in reality it is profoundly dynamic.

Closed-loop (adaptive) neurostimulation fundamentally changes this paradigm by introducing real-time feedback. The device continuously senses neural activity, extracts biomarkers that indicate the patient's clinical state, and automatically adjusts stimulation parameters to maintain the desired therapeutic effect. In Parkinson's disease, the key biomarker is beta-band oscillation power (13-30 Hz) in the subthalamic nucleus (STN). When beta power rises above a threshold — indicating worsening bradykinesia or rigidity — the controller increases stimulation amplitude. When beta power falls — indicating adequate suppression — the controller decreases stimulation to minimize side effects and conserve battery. This creates a continuous control loop that runs 10-100 times per second, adapting therapy to the patient's moment-to-moment neural state.

The clinical benefits are substantial. The Medtronic Percept PC, Boston Scientific Vercise Genus, and Abbott Infinity DBS systems all now offer some form of sensing capability. The NeuroPace RNS System for epilepsy has operated in closed-loop mode since 2013, detecting seizure onset patterns and delivering targeted stimulation to abort electrical storms before they become clinical seizures. But every sensing channel, every feedback path, and every adaptive decision creates new attack surfaces that simply do not exist in open-loop systems.

### 1.2 The Feedback Loop as Attack Surface

In an open-loop system, the attack surface is bounded: compromise the wireless protocol (NL-004) to change parameters, or compromise the firmware (NL-003) to alter behavior. The worst-case outcome is delivery of incorrect but constant stimulation. In a closed-loop system, the attack surface is unbounded in time because the loop itself can amplify small perturbations into large, self-sustaining oscillations. An attacker does not need to directly control the stimulation output — they only need to perturb the sensed signal, manipulate the controller parameters, or introduce timing delays that shift the loop's stability margin.

Consider three fundamentally different attack classes that are unique to closed-loop systems. First, a sensor spoofing attack injects false neural data that causes the controller to make incorrect decisions. If the attacker can make the controller believe beta power is dangerously high, it will increase stimulation beyond therapeutic levels. Second, a delay injection attack adds latency to the feedback path, degrading the phase margin of the control loop. Sufficient delay can push a stable loop into oscillatory instability, where the stimulation and neural response alternate in a growing cycle. Third, a setpoint manipulation attack changes the controller's target, causing it to pursue a pathological objective — for example, maximizing beta power instead of suppressing it.

### 1.3 Clinical Context: Why Timing Matters

The human nervous system operates across multiple timescales, and closed-loop neurostimulation must respect these timescales to be both effective and safe. Neural oscillations relevant to DBS have cycle periods of 33-77 ms (beta band, 13-30 Hz). The control loop must complete one full sense-process-actuate cycle within this period, typically targeting 10-100 ms total latency. Action potentials propagate at 1-100 m/s along axons. Synaptic delays are 1-5 ms. Neuromodulatory effects (dopaminergic, serotonergic) develop over seconds to minutes. The closed-loop controller primarily addresses the fastest timescale — oscillatory dynamics — but its actions have cascading effects on slower timescales.

This timing constraint has direct security implications. An attack that introduces 20 ms of additional latency into a loop operating at 50 ms cycle time has fundamentally different consequences than the same 20 ms delay in a loop operating at 200 ms cycle time. The phase margin — a measure of how close the loop is to instability — degrades proportionally to the delay-to-period ratio. Understanding these timing relationships is essential for analyzing which attacks are feasible and which consequences they produce.

### 1.4 Module Roadmap

This module proceeds through three parts. Part 1 (Sections 1-14) establishes the foundations: control theory prerequisites, closed-loop architecture, attack surface taxonomy, and threat modeling. Part 2 (Sections 15-28) provides deep analysis of specific attack classes — sensor spoofing, controller manipulation, delay injection, feedback bypass, adversarial perturbation — and their detection. Part 3 (Sections 29-42) synthesizes everything into the VIREON benchmark framework (CL-001 through CL-008), digital twin integration, case studies, and open research problems.

---

## Section 2: Control Theory Prerequisites for Neurosecurity

### 2.1 Why Control Theory Matters for Security

Control theory provides the mathematical language to describe how closed-loop neurostimulation systems behave, and more importantly, how they fail. A security analyst who does not understand transfer functions, stability margins, and frequency response cannot distinguish between a benign perturbation and a dangerous one. This section introduces the essential concepts — no prior control theory background is assumed, though learners with engineering backgrounds will find the material familiar.

The central question in control theory is: given a system with inputs and outputs, how do we design a controller that makes the output track a desired reference signal while rejecting disturbances and remaining stable? For neurostimulation, the "plant" is the neural tissue, the "controller" is the PI algorithm running on the implant, the "reference" is the therapeutic setpoint (e.g., target beta power), and the "disturbance" is the natural variability in neural activity — or, from a security perspective, the attacker's injected perturbation.

### 2.2 Transfer Functions and Block Diagrams

A transfer function describes the input-output relationship of a linear, time-invariant (LTI) system in the frequency domain. For a system with input u(t) and output y(t), the transfer function G(s) = Y(s)/U(s) is the ratio of the output Laplace transform to the input Laplace transform, assuming zero initial conditions. In discrete-time (which is what firmware actually implements), we use the z-transform: G(z) = Y(z)/U(z).

For a first-order system with time constant tau and gain K, the continuous transfer function is:

    G(s) = K / (tau * s + 1)

Discretized with sampling period T using the zero-order hold method:

    G(z) = K * (1 - e^(-T/tau)) / (z - e^(-T/tau))

In neurostimulation, the "plant" (neural tissue response to stimulation) is rarely a simple first-order system, but it can often be approximated as one for stability analysis. The stimulation-to-beta-power response has been modeled as a first-order system with tau approximately 100-500 ms, meaning the neural tissue takes several hundred milliseconds to fully respond to a change in stimulation.

A closed-loop system connects the plant output back to the plant input through a controller. The block diagram shows: Reference r(t) → Summing junction (error e = r - y) → Controller C(z) → Plant G(z) → Output y(t), with y(t) also fed back (often through a sensor dynamics block H(z)) to the summing junction. The closed-loop transfer function is:

    T(z) = C(z) * G(z) / (1 + C(z) * G(z) * H(z))

### 2.3 Stability: The Fundamental Safety Criterion

A control system is stable if, for every bounded input, it produces a bounded output (BIBO stability). For discrete-time systems, BIBO stability requires that all poles of the closed-loop transfer function lie inside the unit circle in the z-plane (|z| < 1). If any pole crosses outside the unit circle, the system's response grows without bound — in neurostimulation terms, the stimulation amplitude oscillates with increasing amplitude until the safety monitor intervenes or tissue damage occurs.

The Routh-Hurwitz criterion (for continuous-time) and the Jury stability test (for discrete-time) provide algebraic methods to determine stability without computing pole locations explicitly. However, for neurosecurity analysis, we more commonly use frequency-domain stability margins because they directly quantify "how close" the system is to instability — information that is critical for assessing attack severity.

### 2.4 Gain Margin and Phase Margin

Gain margin (GM) is the factor by which the loop gain can be increased before the system becomes unstable. Phase margin (PM) is the additional phase lag required to bring the system to the stability boundary. Both are derived from the open-loop frequency response C(jw)G(jw)H(jw).

In practical terms for neurostimulation: if the gain margin is 6 dB (factor of 2), the loop can tolerate a doubling of its gain before instability. An attack that increases the controller gain by more than a factor of 2 would push the system unstable. Similarly, if the phase margin is 45 degrees, the loop can tolerate an additional 45 degrees of phase lag. An attack that introduces more than 45 degrees of additional delay-induced phase lag (at the gain crossover frequency) would destabilize the system.

For a loop with sample period T = 10 ms, an additional delay of d samples introduces phase lag of -d * w * T radians at frequency w. At the gain crossover frequency (where the loop gain is 1), if the system has a 45-degree phase margin, the maximum tolerable additional delay is approximately PM / (omega_c * T). For typical closed-loop DBS parameters, this works out to 1-3 additional samples of delay — meaning even small timing attacks can be devastating.

### 2.5 The PI Controller in the Z-Domain

The proportional-integral (PI) controller is the most common algorithm in closed-loop neurostimulation due to its simplicity, robustness, and predictable behavior. In continuous time:

    u(t) = Kp * e(t) + Ki * integral(e(tau), tau=0..t)

Where Kp is the proportional gain, Ki is the integral gain, and e(t) = r(t) - y(t) is the error signal. Discretizing with sample period T using the backward Euler method:

    u[n] = u[n-1] + (Kp + Ki*T) * e[n] - Kp * e[n-1]

This is the form implemented in firmware (NL-003 Section 10). The discrete transfer function is:

    C(z) = (Kp + Ki*T) * z - Kp) / (z - 1)

The PI controller has one zero at z = Kp / (Kp + Ki*T) and one pole at z = 1 (the integrator). The integrator pole on the unit circle is what gives the PI controller zero steady-state error — it will eventually drive the output to exactly match the reference. But the integrator is also the source of potential instability: it accumulates error over time, and if the loop is open-circuited (feedback lost), the integrator winds up to extreme values (integral windup).

### 2.6 Discrete-Time Stability Analysis

To analyze the stability of the complete closed-loop system, we form the characteristic equation:

    1 + C(z) * G(z) * H(z) = 0

The roots of this equation are the closed-loop poles. For a typical closed-loop DBS system with first-order plant and PI controller, the characteristic equation is second-order:

    z^2 + a1*z + a0 = 0

Where a1 and a0 depend on Kp, Ki, T, the plant gain K, and the plant time constant tau. The stability boundary in the (Kp, Ki) parameter space defines the region of safe operation. The VIREON validation framework checks that the current controller parameters lie within this region (or sufficiently far from the boundary).

For the security analyst, this characteristic equation reveals something crucial: the attacker does not need to find a specific "exploit" in the traditional software security sense. They only need to shift the effective parameters (Kp, Ki, T, K, tau) such that the poles move outside the unit circle. This can be achieved by manipulating any component of the loop.

### 2.7 From Control Theory to Attack Classification

The control-theoretic framework gives us a systematic way to classify closed-loop attacks. Each attack perturbs one or more elements of the control loop, and the effect on stability can be predicted from the modified characteristic equation. We identify five fundamental perturbation classes:

| Perturbation Class | Control-Theory Mapping | Attack Example |
|---|---|---|
| Sensor perturbation | Modifies H(z) — sensor dynamics | Injecting false beta power readings |
| Controller perturbation | Modifies C(z) — controller parameters | Changing Kp or Ki values |
| Actuator perturbation | Modifies plant input u(t) | Injecting stimulation commands directly |
| Delay perturbation | Adds phase lag to loop | Buffering sensor data before processing |
| Reference perturbation | Changes setpoint r(t) | Modifying the target beta power |

These five classes form the basis for the detailed attack analysis in Part 2. Each class has distinct detection requirements, countermeasure strategies, and VIREON benchmark scenarios.

---

## Section 3: Closed-Loop DBS Architecture

### 3.1 Functional Decomposition

A closed-loop DBS system decomposes into five functional blocks, each with distinct security properties and attack surfaces. Understanding this decomposition is the prerequisite for analyzing any specific attack.

**Sensing Block:** Electrodes detect neural activity (LFP in the 0.5-500 Hz range for DBS), which is amplified, digitized (typically 16-24 bit ADC at 1-10 kHz), and buffered. The sensing block produces a time-series of voltage samples that represent the neural signal. Security properties include: signal integrity (no injection or modification of samples), authenticity (samples originate from the intended electrodes), and availability (continuous sampling without gaps). The sensing block is the "eye" of the closed-loop system — if the eye is fooled, every downstream decision is corrupted.

**Processing Block:** Raw neural samples pass through the DSP pipeline (NL-002): bandpass filtering (e.g., 5-45 Hz for beta), feature extraction (band power via RMS or spectral estimation), and artifact detection/rejection. The processing block transforms raw voltage into a control variable — typically beta-band power in dB or linear scale. Security properties include: algorithmic integrity (the correct filter coefficients and extraction method are used), consistency (the same processing is applied every cycle), and bounded execution time (the processing completes within the allocated time slot).

**Control Block:** The control algorithm (PI, PID, or more advanced) computes the stimulation adjustment based on the error between the current feature value and the therapeutic setpoint. The control block is where the "decision" is made — how much to change stimulation. Security properties include: parameter integrity (Kp, Ki, setpoint are correct and unmodified), computational correctness (the algorithm produces the mathematically correct output), and bounded output (the control action stays within safe limits).

**Actuation Block:** The control output drives the stimulation circuitry to deliver electrical pulses to the target neural tissue. This includes the current/voltage source, charge-balancing circuitry, and electrode switching matrix. Security properties include: parameter limits (amplitude, frequency, pulse width within safe ranges), charge balance (no net DC current through tissue), and output integrity (the commanded stimulation matches the delivered stimulation).

**Monitoring Block:** The safety monitor (introduced in NL-003 Section 12) provides an independent check on the closed-loop system. It watches for conditions that indicate malfunction or attack: stimulation exceeding limits, loop instability (oscillatory behavior), sensor anomalies (signal clipping, flatline, sudden offset), and excessive integral windup. The monitor can force the system into a safe state (stimulation off, open-loop fallback, or emergency mode). Security properties include: independence from the control path (the monitor cannot be disabled by the same mechanism that controls the loop), coverage (the monitor checks all critical conditions), and response time (the monitor detects and responds to dangerous conditions within the safety window).

### 3.2 Signal Flow and Timing

In a typical closed-loop DBS system with 10 ms cycle time, the signal flow proceeds as follows. During the first 2 ms, the ADC samples neural activity at 1 kHz, collecting 20 samples per channel. During ms 2-4, the DSP pipeline filters and extracts features from these samples. During ms 4-6, the control algorithm computes the new stimulation parameters. During ms 6-8, the new parameters are loaded into the stimulation hardware. During ms 8-10, stimulation is delivered while the system prepares for the next cycle. The safety monitor runs concurrently, checking conditions on every cycle.

This timing diagram reveals several security-relevant properties. The sensing window and the stimulation window are temporally separated — the system does not sense during stimulation (to avoid stimulation artifact contaminating the neural signal). This blanking period creates a dead time in the feedback loop that reduces the phase margin. An attacker who can extend the blanking period (e.g., by forcing the stimulation to start earlier or end later) increases the effective dead time and pushes the loop toward instability.

### 3.3 Data Types and Interfaces

The interfaces between functional blocks are critical security boundaries. Each interface carries specific data types with specific ranges, rates, and integrity requirements.

- **Sense → Process:** Raw ADC samples (int16 or int24, 1-10 kHz per channel). Volume: 2-30 kB/s per channel. Integrity: critical (corrupted samples produce incorrect features). Latency: < 1 ms.
- **Process → Control:** Feature value (float32, typically 1-100 Hz update rate for beta power). Volume: 4-400 B/s. Integrity: critical (wrong feature → wrong control decision). Latency: < 5 ms from sample to feature.
- **Control → Actuate:** Stimulation parameters (amplitude 0-10 V in 0.1 V steps, frequency 2-200 Hz, pulse width 10-450 us). Volume: 6-12 bytes per update at 10-100 Hz. Integrity: safety-critical (wrong parameters → tissue damage). Latency: < 2 ms.
- **Control/Actuate → Monitor:** Stimulation parameters + computed features (for monitoring). Volume: 10-20 bytes per cycle. Integrity: high (monitor must have accurate data). Latency: concurrent with control path.

### 3.4 Redundancy and Fail-Safe Design

Medical-grade closed-loop systems employ multiple layers of redundancy to prevent dangerous failures. The sensing block may use multiple electrodes on the same lead (bipolar vs. monopolar configurations) to cross-validate signals. The processing block may run a simplified feature extraction in parallel to check the primary pipeline's output. The control block has hard limits on output range and rate of change. The actuation block has hardware current limiters and charge-balance verification circuits. The monitor operates on an independent processing path with its own ADC read (or at least independent feature computation).

From a security perspective, redundancy creates both challenges and opportunities. The challenge is that the attacker must compromise multiple independent paths simultaneously to succeed, significantly raising the bar. The opportunity is that inconsistencies between redundant paths are themselves detectable anomalies that can serve as attack indicators. However, redundancy also increases complexity, and complexity is the enemy of security — each redundant path is itself an attack surface.

---

## Section 4: Neural Signal Models for Closed-Loop Control

### 4.1 Beta-Band Oscillations as Biomarker

In Parkinson's disease, the subthalamic nucleus (STN) exhibits excessive synchronization in the beta frequency band (13-30 Hz). This pathological beta activity correlates strongly with bradykinesia (slowness of movement) and rigidity. When DBS is applied to the STN at sufficient amplitude, beta power decreases and motor symptoms improve. This relationship — high beta = bad, low beta = good — forms the basis for closed-loop DBS.

The neural signal model for closed-loop control must capture several key properties of beta oscillations. First, beta power fluctuates naturally on multiple timescales: fast fluctuations (100-500 ms) due to neural dynamics, medium fluctuations (1-10 s) due to behavioral state changes, and slow fluctuations (minutes to hours) due to medication cycles and circadian rhythms. Second, beta power is modulated by stimulation — the relationship is approximately first-order with a time constant of 100-500 ms (stimulation increases → beta decreases). Third, beta power exhibits stochastic variability — even in a steady behavioral state, beta power varies with a coefficient of variation of 10-30%.

### 4.2 Stimulus-Response Model

The relationship between stimulation amplitude and beta power can be modeled as a static nonlinear function followed by a first-order linear dynamic. The static nonlinearity captures the observation that beta power decreases sigmoidally with increasing stimulation: minimal effect at low amplitudes, steep decrease in the therapeutic range, and diminishing returns at high amplitudes. The first-order dynamics capture the temporal response:

    tau * d(beta)/dt + beta = f(stim_amplitude)

Where f() is the static nonlinear function (sigmoidal), and tau is the response time constant (100-500 ms). Discretized with sample period T:

    beta[n+1] = alpha * beta[n] + (1 - alpha) * f(u[n])

Where alpha = exp(-T/tau) is the decay factor. For T = 10 ms and tau = 200 ms, alpha = 0.951. This means the current beta value retains 95.1% of the previous value and incorporates 4.9% of the new stimulus effect.

### 4.3 Signal Model for Simulation

For the VIREON digital twin and lab simulations, we need a complete neural signal model that generates realistic beta-band time series. The model must produce signals that: (a) have the correct spectral content (peak power in 13-30 Hz), (b) exhibit natural variability, (c) respond to stimulation changes with appropriate dynamics, and (d) include realistic noise and artifacts.

The simulation signal model combines three components:

1. **Oscillatory component:** Sum of 3-5 sinusoids in the beta range with slowly varying amplitudes and phases. This captures the narrowband nature of beta oscillations.
2. **Background component:** 1/f (pink) noise filtered to the beta band, representing the broadband neural background.
3. **Sensor noise component:** White Gaussian noise at the ADC noise floor, representing thermal noise in the electrode-tissue interface and amplification chain.

The total signal is: x(t) = A(t) * sin(2*pi*f_beta*t + phi(t)) + n_pink(t) + n_white(t)

Where A(t) varies slowly (1-10 s timescale) to simulate natural beta modulation, and f_beta is the dominant beta frequency (typically 18-22 Hz for Parkinson's STN). The amplitude A(t) is modulated by the stimulation effect: A(t) = A0 / (1 + k * u(t-tau_d)), where u is the stimulation amplitude, k is the coupling strength, and tau_d is the neural delay.

### 4.4 Artifact Models

Real neural recordings contain artifacts that the processing pipeline must handle — and that an attacker can exploit. The three most relevant artifact classes for closed-loop security are:

**Stimulation artifact:** The stimulation pulse itself creates a large voltage transient that can saturate the amplifier. In properly designed systems, a blanking period (0.1-1 ms after each pulse) prevents the artifact from entering the ADC. If an attacker can defeat the blanking circuit (e.g., by modifying timing registers), the artifact will be processed as neural signal, corrupting the feature extraction.

**Movement artifact:** Patient movement (muscle EMG, electrode micro-motion) produces broadband electrical activity that overlaps the beta band. This is indistinguishable from genuine beta activity using spectral features alone. A sophisticated attacker could inject signals that mimic movement artifacts to mask their sensor spoofing.

**Environmental interference:** Power line noise (50/60 Hz), RF interference from communications, and electromagnetic interference from other medical devices can all contaminate neural recordings. These are typically handled by notch filters and shielded designs, but the filters themselves can be attacked (NL-002 Section 8).

---

## Section 5: The PI/PID Controller in Neurostimulation

### 5.1 Why PI Instead of PID or Advanced Control

The proportional-integral (PI) controller is overwhelmingly preferred in implantable neurostimulation for three reasons: computational simplicity (few multiply-accumulate operations per cycle), robustness (PI controllers tolerate significant model uncertainty without instability), and clinical interpretability (clinicians can understand how Kp and Ki map to therapeutic behavior). Proportional-derivative (PID) controllers are rarely used because the derivative term amplifies high-frequency noise — problematic when the sensed signal is neural activity with inherently high noise levels. Advanced controllers (model predictive control, adaptive control, LQG) are theoretically superior but require significantly more computation and are harder to validate for safety-critical applications.

### 5.2 Tuning the PI Controller for DBS

The PI controller for closed-loop DBS must be tuned to achieve three conflicting objectives: fast response (quickly suppress pathological beta), stability (never oscillate or diverge), and smooth operation (avoid rapid stimulation changes that cause side effects). The tuning parameters Kp and Ki define the trade-off between these objectives.

In clinical practice, PI tuning for closed-loop DBS follows the "gentle adaptation" philosophy. The proportional gain Kp is set relatively low (typically 0.01-0.1) so that each control step makes a small adjustment. The integral gain Ki is set very low (typically 0.001-0.01) so that the integrator slowly accumulates error, providing gradual long-term correction without overshoot. This conservative tuning prioritizes stability and patient comfort over speed of response.

For the VIREON simulation, we use a representative tuning: Kp = 0.05, Ki = 0.005, with sample period T = 10 ms. The stimulation amplitude ranges from 0 to 7.5 mA, with a default setpoint of beta power = 0 dB (relative to baseline). The controller adjusts amplitude to drive beta power toward 0 dB.

### 5.3 Integral Windup and Anti-Windup

Integral windup is a critical safety concern in PI-controlled neurostimulation. When the actuator saturates (stimulation reaches its maximum), the error signal remains nonzero, and the integrator continues to accumulate. The accumulated integral can grow very large, causing massive overshoot when the error finally reverses. In neurostimulation, this manifests as: the patient enters a state of high beta (e.g., stress), the controller increases stimulation to maximum, the integrator winds up, then when beta naturally decreases, the wound-up integrator maintains maximum stimulation far longer than necessary, causing side effects.

Anti-windup mechanisms prevent this. The most common approach in neurostimulators is conditional integration: the integrator only accumulates when the control output is not saturated. When the output is saturated, the integrator holds its value (or slowly decays). This is called "clamping anti-windup" and is implemented as:

    if output == min or output == max:
        integrator holds  # do not accumulate
    else:
        integrator += Ki * error * T

An attacker who disables anti-windup (by modifying the firmware flag or the saturation check) can trigger windup behavior, causing the controller to deliver maximum stimulation for extended periods even after the attack stimulus is removed.

### 5.4 Rate Limiting and Output Clamping

Beyond anti-windup, the controller implements two additional safety mechanisms. Rate limiting restricts how fast the stimulation amplitude can change between cycles (e.g., maximum 0.1 mA per 10 ms cycle). This prevents the controller from making abrupt changes even if the error signal is large, and it limits the attack impact of momentary sensor spikes. Output clamping enforces absolute limits on the stimulation parameters (amplitude 0-7.5 mA, frequency 2-185 Hz, pulse width 60-210 us).

These mechanisms are implemented in the control block firmware (NL-003) and checked by the safety monitor. From a security perspective, rate limiting is a double-edged sword: it limits attack impact but also limits the system's ability to respond rapidly to genuine physiological changes. An attacker who can increase the rate limit (e.g., by modifying the firmware parameter) removes this protection; an attacker who can decrease it (e.g., by modifying the parameter to 0) can prevent the controller from making any adjustments at all, effectively disabling closed-loop operation.

---

## Section 6: Discrete-Time Control Implementation

### 6.1 Firmware Implementation Details

The PI controller from Section 5 is implemented in firmware as a discrete-time difference equation. On an ARM Cortex-M4 (typical for neurostimulators), the implementation uses fixed-point arithmetic for efficiency, though floating-point is also used on Cortex-M4F/M7 parts with hardware FPU. The implementation must satisfy hard real-time constraints: the control computation must complete within its allocated time slot (typically 1-2 ms out of a 10 ms cycle).

The firmware implementation (extending NL-003 Section 10) includes: (a) input validation — check that the feature value is within plausible range, (b) error computation — e = setpoint - measured_beta, (c) proportional term — p_term = Kp * e, (d) integral update — i_term += Ki * e * T (with anti-windup), (e) output computation — u = p_term + i_term, (f) rate limiting — clamp du/dt to maximum rate, (g) output clamping — clamp u to [u_min, u_max], (h) output to actuation block.

### 6.2 Numerical Precision and Security

The choice between fixed-point and floating-point arithmetic has security implications. Fixed-point arithmetic (e.g., Q15 or Q31 format) has predictable rounding behavior and bounded error, but is susceptible to overflow if intermediate results exceed the representable range. An attacker who can cause overflow (e.g., by providing extreme feature values) can make the controller produce undefined or incorrect outputs. Floating-point arithmetic has larger dynamic range but introduces rounding that is harder to predict, and IEEE 754 special values (NaN, Infinity) can propagate through computations if not explicitly checked.

For VIREON, we recommend IEEE 754 single-precision (float32) with explicit checks for NaN, Infinity, and subnormal numbers at every control block interface. Any special value should trigger a safety monitor alert and force the controller to hold its previous output. This is a defense-in-depth measure: even if an attacker causes a NaN to enter the control computation, the system does not deliver undefined stimulation.

### 6.3 State Machine for Closed-Loop Operation

The closed-loop system operates through a state machine that defines valid transitions and security boundaries. States include: INIT (power-on self-test, calibration), OPEN_LOOP (fixed parameters, no feedback), CLOSED_LOOP (adaptive control active), SAFE_MODE (stimulation off, monitoring only), and FAULT (non-recoverable error, requires clinician intervention). Transitions between states have security requirements: OPEN_LOOP → CLOSED_LOOP requires parameter validation and safety check completion; CLOSED_LOOP → SAFE_MODE can be triggered by the safety monitor, clinician command, or detected attack; FAULT requires explicit clinician intervention to clear.

An attacker who can force unauthorized state transitions creates dangerous scenarios. Forcing INIT → CLOSED_LOOP without completing calibration could use stale or incorrect calibration data. Forcing CLOSED_LOOP → OPEN_LOOP with specific parameters could set dangerous fixed stimulation. Forcing SAFE_MODE → CLOSED_LOOP without proper checks could resume operation with corrupted controller state.

---

## Section 7: Sensing Pipeline Security Properties

### 7.1 Threat Model for the Sensing Block

The sensing block converts neural activity into digital samples. The attacker's goal is to make the processing block receive data that does not accurately represent the actual neural activity. Attack vectors include:

**Direct signal injection:** Using an external electromagnetic source to induce voltages on the sensing electrodes. This requires physical proximity and sufficient power to overcome the electrode-tissue impedance (typically 1-10 kohm at 1 kHz). The injection must be in the beta band to affect the control variable, and it must be coherent across multiple sensing cycles to have a sustained effect on the controller.

**ADC tampering:** Modifying the ADC configuration (input multiplexer, gain, reference voltage, sampling rate) through firmware exploitation (NL-003). Changing the gain alters the relationship between neural voltage and digital code, effectively scaling the sensed signal. Changing the reference voltage has a similar effect. Changing the sampling rate affects the Nyquist frequency and can cause aliasing.

**Sample substitution:** Replacing genuine neural samples with attacker-controlled data in the buffer between the ADC and the DSP pipeline. This requires firmware-level access (memory corruption, DMA manipulation) or a timing attack that overwrites the buffer during the handoff window.

**Timing manipulation:** Altering the sampling clock to introduce jitter or skew. Timing jitter broadens the apparent spectral content of narrowband signals, potentially spreading beta power into adjacent bands and reducing the extracted feature value. Timing skew (systematic offset) shifts apparent frequencies, potentially moving the beta peak outside the analysis band.

### 7.2 Sensor Integrity Metrics

To detect sensing attacks, the VIREON validation framework defines sensor integrity metrics:

- **Signal statistics consistency:** Mean, variance, kurtosis, and skewness of the sensed signal should remain within physiologically plausible ranges. Sudden changes in these statistics indicate potential injection or tampering.
- **Spectral consistency:** The power spectral density shape (not just the beta band power) should remain consistent with the expected neural signal model. An injected narrowband signal will have a different spectral shape than genuine beta oscillations.
- **Cross-channel consistency:** For multi-electrode configurations, beta power on adjacent contacts should be correlated. An injection on one channel that does not appear on adjacent channels is suspicious.
- **Temporal consistency:** Beta power should not change faster than the neural response time constant allows. A step change in beta power (faster than ~100 ms) is physiologically implausible and indicates signal injection.

### 7.3 Blanking Period Security

The blanking period (the time window during and after stimulation when the ADC does not sample) is a critical security mechanism. It prevents stimulation artifact from entering the control loop. However, the blanking period also creates a security vulnerability: it represents a regular, predictable gap in sensing that an attacker can exploit.

If the blanking period is too short, stimulation artifact leaks into the sensed signal, adding a periodic component at the stimulation frequency that can corrupt beta power estimation. If the blanking period is too long, the effective feedback delay increases, degrading the phase margin. An attacker who can modify blanking duration (through firmware parameter tampering) can simultaneously inject artifact (by shortening) and degrade stability (by lengthening, if done strategically to be below detection threshold).

---

## Section 8: Actuation Pipeline Security Properties

### 8.1 Threat Model for the Actuation Block

The actuation block converts digital stimulation commands into electrical current delivered to neural tissue. Attack vectors include:

**Command injection:** Injecting unauthorized stimulation commands that bypass the control algorithm. This can be achieved through wireless protocol exploitation (NL-004), firmware exploitation (NL-003), or hardware fault injection. The injected command specifies amplitude, frequency, pulse width, and duration directly, overriding the controller's output.

**Parameter modification:** Changing the stimulation parameters computed by the controller after they leave the control block but before they reach the stimulation hardware. This requires access to the inter-block communication (shared memory, register writes) and can be achieved through firmware exploitation.

**Hardware subversion:** Modifying the stimulation hardware's behavior — for example, disabling the current limiter, changing the voltage reference, or rewiring the electrode switching matrix. This requires physical access or extremely sophisticated firmware exploitation that accesses hardware configuration registers.

### 8.2 Charge Balance Safety

Charge balance is the fundamental safety mechanism for neural stimulation. Each stimulation pulse delivers a brief burst of positive current (cathodic phase) followed by an equal or greater burst of negative current (anodic phase). The net charge delivered over a complete pulse cycle must be zero (or negligibly small) to prevent electrochemical reactions at the electrode-tissue interface that can cause tissue damage, electrode corrosion, and pH shifts.

In firmware, charge balance is enforced by: (a) requiring anodic phase charge >= cathodic phase charge, (b) monitoring the DC offset of the stimulation waveform, (c) implementing a hardware charge-recovery circuit that passively balances any residual charge. An attacker who can disable charge-balance checking can cause electrochemical damage to neural tissue through sustained DC stimulation.

### 8.3 Stimulation Parameter Limits

The actuation block enforces absolute limits on all stimulation parameters. These limits are stored in protected firmware memory and cannot be modified through the wireless interface (they require a firmware update with clinician authentication). The typical limits for DBS are: amplitude 0-7.5 mA (current-controlled) or 0-10.5 V (voltage-controlled), frequency 2-185 Hz, pulse width 60-210 us. The duty cycle (pulse width * frequency) must remain below 50% to allow sufficient charge recovery time.

The safety monitor independently verifies that the stimulation parameters are within limits on every cycle. If a limit violation is detected, the monitor forces the system into SAFE_MODE. An attacker who can modify the limit values (through firmware exploitation) or disable the monitor's limit checking can deliver stimulation outside the safe range.

---

## Section 9: Feedback Loop Timing and Latency

### 9.1 Sources of Latency in the Closed Loop

The total loop latency — the time from neural event to stimulation response — determines the closed-loop system's performance and stability. Latency has four components:

1. **Sensing latency:** Time from neural event to digitized sample (typically 0.1-1 ms, dominated by ADC conversion time and any analog filtering delay).
2. **Processing latency:** Time from raw sample to extracted feature (typically 1-5 ms, dominated by the DSP pipeline including filtering, windowing, and spectral estimation).
3. **Control latency:** Time from feature to stimulation command (typically 0.1-1 ms, dominated by the control algorithm computation).
4. **Actuation latency:** Time from command to stimulation delivery (typically 0.1-0.5 ms, dominated by the stimulation hardware setup time).

Additionally, there is an inherent **neural delay** — the time for the stimulation to modulate neural activity (typically 10-50 ms, depending on the neural pathway). This delay is part of the plant dynamics and cannot be reduced.

### 9.2 Latency as Attack Vector

An attacker who can increase the loop latency (without being detected) degrades the phase margin of the control system. The phase margin loss due to additional delay d at frequency omega is:

    PM_loss = omega * d (radians) = omega * d * 180 / pi (degrees)

For a closed-loop DBS system with a gain crossover frequency of 5 rad/s (0.8 Hz), an additional delay of 100 ms causes a phase margin loss of 0.5 radians (28.6 degrees). If the original phase margin was 45 degrees, the remaining margin is only 16.4 degrees — dangerously close to instability.

Delay attacks can be implemented through several mechanisms: (a) buffering sensor data before processing (software delay), (b) inducing excessive processing time (e.g., by triggering complex DSP operations or faulting cache), (c) delaying the control output (modifying inter-block communication timing), or (d) introducing jitter that effectively increases average delay.

### 9.3 Jitter and Its Security Implications

Latency jitter — variation in the loop delay from cycle to cycle — has different effects than constant delay. Constant delay shifts the phase response uniformly; jitter introduces uncertainty in the phase response, which can cause intermittent instability. A loop that is stable with constant delay may become unstable when the delay varies because the controller's integral term accumulates error during long-delay cycles and overshoots during short-delay cycles.

For the VIREON digital twin, we model jitter as a random variable added to the base latency each cycle. The standard deviation of jitter (jitter_sigma) is a security parameter: low jitter (< 1 ms) is normal, moderate jitter (1-5 ms) indicates potential interference, and high jitter (> 5 ms) indicates likely attack or system malfunction. The safety monitor tracks jitter statistics and flags excessive values.

### 9.4 Sampling Rate and Aliasing

The loop's sampling rate (control cycle frequency) determines the maximum frequency of neural dynamics that the controller can address. According to the Nyquist criterion, the sampling rate must be at least twice the highest frequency of interest. For beta-band control (13-30 Hz), a minimum sampling rate of 60 Hz (16.7 ms period) is required, but practical systems use 100 Hz (10 ms period) to provide adequate phase margin.

If an attacker can reduce the effective sampling rate (e.g., by causing missed cycles through buffer overflows, interrupt blocking, or timer tampering), two dangerous effects occur. First, the Nyquist frequency decreases, potentially allowing aliasing of high-frequency noise or artifacts into the beta band. Second, the discrete-time stability properties change — a controller that is stable at 100 Hz may become unstable at 50 Hz because the discrete-time poles shift. This is a subtle but devastating attack that would be difficult to detect without explicit monitoring of the effective sampling rate.

---

## Section 10: Safety Monitor Architecture in Closed-Loop Context

### 10.1 Monitor Functions Specific to Closed-Loop

The safety monitor (NL-003 Section 12) takes on additional responsibilities in a closed-loop system beyond its open-loop duties. In closed-loop mode, the monitor must detect and respond to:

- **Stimulation limit violations:** Amplitude, frequency, pulse width, charge per pulse, and duty cycle exceed their programmed limits.
- **Loop instability:** Oscillatory behavior in the stimulation output or the sensed signal, detected via zero-crossing rate analysis, autocorrelation, or spectral peak detection.
- **Sensor anomalies:** Signal clipping (saturation), flatline (loss of signal), sudden DC offset shift, or spectral anomaly (unexpected frequency content).
- **Controller anomalies:** Integral windup (integrator value exceeds threshold), output rate violation (stimulation changing too fast), NaN/Infinity in control path.
- **Timing anomalies:** Missed control cycles, excessive jitter, delay exceeding threshold.

### 10.2 Independence Requirements

The safety monitor must be architecturally independent from the control path to provide defense in depth. This means: (a) the monitor runs on a separate hardware timer or RTOS task with higher priority than the control loop, (b) the monitor reads from an independent ADC channel or independently computes features from the raw samples, (c) the monitor's memory is protected from the control firmware (using MPU regions), (d) the monitor cannot be disabled or reconfigured through the same wireless interface as the control parameters.

In practice, achieving full independence is expensive in terms of hardware resources. Many commercial devices implement partial independence: the monitor runs at higher priority but shares the ADC with the control path, or the monitor computes features independently but uses the same raw samples. For VIREON, we define three levels of monitor independence: Level 1 (shared everything, lowest security), Level 2 (independent computation, shared sensing), Level 3 (fully independent sensing and computation, highest security).

### 10.3 Monitor Response Actions

When the monitor detects an anomaly, it can take one of several response actions, ordered by severity:

1. **Log and continue:** Record the anomaly for clinician review but allow continued operation. Used for minor anomalies (slight jitter increase, brief spectral anomaly).
2. **Increase monitoring rate:** Switch from periodic monitoring to every-cycle monitoring. Used when an anomaly pattern is detected but has not yet reached the threshold for intervention.
3. **Switch to open-loop:** Force the controller to hold its current output (or revert to a safe default) while maintaining sensing for diagnostics. This is the most common safety response — it preserves therapeutic benefit while removing the feedback vulnerability.
4. **Reduce stimulation:** Decrease stimulation to a safe minimum level while maintaining some therapeutic effect. Used when the anomaly suggests overstimulation risk.
5. **Disable stimulation:** Turn off stimulation entirely. Used for severe anomalies (detected instability, sensor failure, limit violation). The system remains in monitoring mode to record diagnostic data.
6. **Emergency shutdown:** Turn off stimulation and cease all sensing. Used only for non-recoverable hardware failures. Requires clinician intervention to restart.

An attacker's goal might be to prevent the monitor from escalating beyond level 1 (logging), or to trigger a false level 5 (disabling stimulation) as a denial-of-service attack.

---

## Section 11: Closed-Loop Attack Surface Taxonomy

### 11.1 The Five Attack Surfaces

Building on the functional decomposition (Section 3) and the control-theoretic perturbation classes (Section 2.7), we define five attack surfaces for closed-loop neurostimulation:

**AS-1: Sensing Surface** — Attacks that modify or inject data at the sensor-to-processor interface. Includes: electromagnetic injection on electrodes, ADC configuration tampering, sample buffer manipulation, timing/sampling clock manipulation. The sensing surface is the most accessible to external attackers (proximity-based EM injection) and the hardest to detect (the modified data looks like neural activity).

**AS-2: Processing Surface** — Attacks that modify the DSP pipeline's behavior. Includes: filter coefficient tampering, window function manipulation, feature extraction algorithm substitution, artifact detector bypass. The processing surface requires firmware-level access (AS-2 attacks are typically preceded by NL-003 firmware exploitation) but provides fine-grained control over the control variable.

**AS-3: Controller Surface** — Attacks that modify the control algorithm's parameters or computation. Includes: Kp/Ki manipulation, setpoint modification, anti-windup disable, rate limit modification, output clamp modification. The controller surface is the most impactful for stability attacks — small parameter changes can shift the closed-loop poles dramatically.

**AS-4: Actuation Surface** — Attacks that modify the stimulation output. Includes: command injection (bypassing controller), parameter modification (intercepting controller output), hardware subversion (current limiter disable, charge-balance bypass). The actuation surface has the most immediate physical impact — incorrect stimulation directly affects neural tissue.

**AS-5: Monitor Surface** — Attacks that disable, blind, or subvert the safety monitor. Includes: monitor disable (firmware flag), monitor threshold increase (allowing larger violations before response), monitor timing desynchronization (causing monitor to check stale data), false alarm flooding (causing monitor to be ignored). The monitor surface is the highest-value target for sophisticated attackers — disabling the monitor removes the last line of defense.

### 11.2 Attack Surface Interaction

The five attack surfaces are not independent — attacks on one surface can enable or amplify attacks on another. For example, a sensing surface attack (AS-1) that injects gradually increasing beta power causes the controller (AS-3) to increase stimulation, which the monitor (AS-5) may interpret as a genuine clinical event and allow. Only by correlating information across surfaces — the spectral shape of the injected signal (inconsistent with genuine beta), the timing of the increase (too fast for neural dynamics), and the cross-channel consistency (injection on one channel only) — can the system detect the attack.

This interaction is why VIREON's validation framework uses multi-surface correlation. Individual surface checks (e.g., parameter range check on AS-3) provide baseline protection, but the real security comes from cross-surface correlation: does the stimulation profile make sense given the sensed neural state? Is the controller behavior consistent with the feature trajectory? Is the monitor seeing the same data as the controller?

### 11.3 Attack Access Requirements

| Attack Surface | Minimum Access | Typical Vector | Detection Difficulty |
|---|---|---|---|
| AS-1 (Sensing) | Physical proximity | EM injection, electrode coupling | Very High |
| AS-2 (Processing) | Firmware exploit | NL-003 buffer overflow, OTA | High |
| AS-3 (Controller) | Firmware or wireless | Parameter write via protocol | Medium |
| AS-4 (Actuation) | Firmware or wireless | Command injection via protocol | Low (immediate physical impact) |
| AS-5 (Monitor) | Firmware exploit | NL-003 MPU misconfiguration | Very High (silent failure) |

---

## Section 12: STRIDE Threat Model for Closed-Loop Systems

### 12.1 Applying STRIDE to Closed-Loop Architecture

STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) provides a systematic framework for identifying threats. Applied to the closed-loop DBS system:

**Spoofing:** An attacker spoofs neural sensor data (AS-1), making the controller believe the patient's neural state is different from reality. This is the most dangerous STRIDE threat for closed-loop systems because the controller trusts its sensor input by design. Unlike IT systems where input validation is standard, neural signals are inherently variable and difficult to validate against an "expected" pattern.

**Tampering:** An attacker modifies controller parameters (AS-3), processing pipeline (AS-2), or stimulation limits (AS-4). Tampering attacks leverage the firmware and protocol vulnerabilities analyzed in NL-003 and NL-004. In closed-loop context, tampering is more dangerous because the feedback loop amplifies the effect: a small parameter change can cause the loop to oscillate or diverge.

**Repudiation:** An attacker performs an attack (e.g., parameter manipulation via wireless) and the system cannot prove it happened. In closed-loop systems, repudiation is particularly concerning because the therapy logs may show "normal" adaptive behavior when in fact the controller was responding to an injected signal. Without forensic evidence, the clinician cannot distinguish between genuine adaptation and attack-induced behavior.

**Information Disclosure:** Neural signal data leaks to an unauthorized party. Closed-loop systems generate continuous neural recordings, which contain highly sensitive neurophysiological information. If the wireless telemetry (NL-004) is compromised, an eavesdropper can reconstruct the patient's neural state in real time, revealing cognitive state, emotional responses, and motor intentions.

**Denial of Service:** The attacker prevents the closed-loop system from providing therapy. Methods include: triggering false safety monitor alarms (causing the system to shut down), causing persistent sensor anomalies (forcing open-loop fallback), or flooding the wireless channel (preventing clinician communication). In closed-loop systems, DoS is not just inconvenient — loss of adaptive therapy can cause immediate clinical deterioration.

**Elevation of Privilege:** An attacker gains the ability to modify parameters that should require clinician authorization. In closed-loop systems, this includes modifying the therapeutic setpoint, changing controller tuning, disabling the safety monitor, or altering stimulation limits. Elevation of privilege in a closed-loop system gives the attacker control over the feedback loop itself — the highest-impact attack scenario.

### 12.2 Threat-Attack-Benchmark Mapping

Each STRIDE threat maps to one or more attack classes (detailed in Part 2) and one or more VIREON benchmarks (CL-001 through CL-008, defined in Part 3):

| STRIDE Threat | Attack Class (Part 2) | Benchmark (Part 3) |
|---|---|---|
| Spoofing | Sensor spoofing (Sec 15), Adversarial perturbation (Sec 20) | CL-001, CL-002 |
| Tampering | Controller manipulation (Sec 16), Setpoint modification (Sec 17) | CL-003, CL-004 |
| Repudiation | All attacks with forensic evasion | CL-008 |
| Information Disclosure | Telemetry interception (NL-004) | CL-007 |
| Denial of Service | Feedback bypass (Sec 19), Monitor evasion (Sec 25) | CL-005, CL-006 |
| Elevation of Privilege | Controller manipulation (Sec 16), Monitor surface (AS-5) | CL-003, CL-006 |

---

## Section 13: Attack Trees — Closed-Loop Destabilization

### 13.1 Root Goal: Destabilize the Closed-Loop System

The primary attack tree has the root goal: "Cause the closed-loop DBS system to deliver unsafe stimulation or cease therapeutic operation." We decompose this into three sub-goals: (A) Cause oscillatory instability, (B) Cause runaway stimulation, (C) Cause therapeutic failure (therapy stops working). Each sub-goal has multiple attack paths.

**Sub-goal A: Oscillatory Instability.** This requires pushing at least one closed-loop pole outside the unit circle. Attack paths:
- A1: Increase controller gain (modify Kp and/or Ki via AS-3) until the characteristic equation has a root with |z| > 1.
- A2: Introduce sufficient delay (via AS-1 or AS-2 timing manipulation) to reduce phase margin below zero.
- A3: Modify plant dynamics (via AS-4, e.g., stimulating at a frequency that resonates with the neural tissue) to shift the plant poles.
- A4: Combine A1 and A2 with smaller individual perturbations that are each below detection thresholds but together exceed the stability boundary.

**Sub-goal B: Runaway Stimulation.** This requires driving the stimulation to its maximum and keeping it there.
- B1: Spoof sensor data to indicate maximum pathological beta power (AS-1), causing the controller to request maximum stimulation.
- B2: Modify setpoint to an unachievable value (AS-3), causing permanent positive error and maximum output.
- B3: Disable anti-windup (AS-3), wait for natural beta fluctuation to cause windup, then remove the trigger.
- B4: Inject command directly to actuation block (AS-4), bypassing controller entirely.

**Sub-goal C: Therapeutic Failure.** This requires the system to deliver no effective therapy while appearing to function normally.
- C1: Spoof sensor data to indicate perfect therapeutic state (zero beta power), causing the controller to reduce stimulation to minimum.
- C2: Introduce delay sufficient to make the controller unstable, triggering the safety monitor to switch to open-loop with default (possibly suboptimal) parameters.
- C3: Modify the setpoint to the current beta power value, creating zero error and zero control action (setpoint tracking attack).
- C4: Blind the monitor (AS-5) while performing any of C1-C3, preventing automatic fallback.

### 13.2 Attack Tree for Safety Monitor Evasion

A critical sub-tree addresses how an attacker evades the safety monitor while performing the primary attacks above:
- M1: Disable the monitor entirely (firmware flag modification via AS-5). High impact but likely detectable by firmware integrity checks.
- M2: Increase monitor detection thresholds (AS-5) so that attack-induced anomalies fall below the alarm level. Requires understanding the specific thresholds.
- M3: Perform the attack slowly enough that the monitor interprets the changes as natural drift. Exploits the tension between sensitivity (detecting attacks) and specificity (avoiding false alarms).
- M4: Desynchronize the monitor's timing so it checks stale data (AS-5 timing manipulation). The monitor sees normal values while the control loop operates on corrupted values.
- M5: Flood the monitor with false alarms (AS-5) until the clinician disables or ignores the alarm system. Social engineering combined with technical attack.

---

## Section 14: Failure Mode Classification

### 14.1 Failure Mode Categories for Closed-Loop Systems

Failure modes in closed-loop neurostimulation systems are classified by their cause, effect, and detectability. Understanding failure modes is essential for designing the safety monitor and for distinguishing between genuine failures and attacks.

**F1: Sensor Failure.** The sensing block produces incorrect data due to electrode migration, lead fracture, amplifier failure, or ADC malfunction. Effects: incorrect feature extraction, wrong control decisions, inappropriate stimulation. Detection: signal statistics (flatline, clipping, noise floor change), cross-channel consistency, impedance monitoring. Distinction from attack: sensor failures typically affect all frequency bands and develop gradually (electrode migration) or suddenly but permanently (lead fracture), while attacks are often band-specific and can be intermittent.

**F2: Processing Failure.** The DSP pipeline produces incorrect features due to firmware bug, coefficient corruption, or computational error (overflow, NaN). Effects: corrupted control variable, inappropriate stimulation adjustments. Detection: feature value range check, comparison with parallel simplified processing, output consistency check. Distinction from attack: processing failures are typically deterministic and repeatable (same input always produces wrong output), while sensor spoofing attacks produce controlled, goal-directed perturbations.

**F3: Controller Failure.** The control algorithm produces incorrect outputs due to parameter corruption, numerical error, or algorithmic bug. Effects: incorrect stimulation adjustments, potential instability. Detection: output range check, rate-of-change check, stability monitor. Distinction from attack: controller failures are usually consistent (same wrong behavior every cycle) while attacks may be time-varying.

**F4: Actuation Failure.** The stimulation hardware delivers incorrect stimulation due to current source failure, electrode short/open, or charge-balance circuit failure. Effects: under-stimulation or over-stimulation, potential tissue damage. Detection: impedance monitoring, delivered-charge verification, electrode voltage monitoring. Distinction from attack: actuation failures are hardware-level and affect the physical stimulation waveform, while command injection attacks produce correct waveforms with wrong parameters.

**F5: Timing Failure.** The control loop timing is disrupted due to timer fault, RTOS scheduling error, interrupt priority inversion, or computational overload. Effects: increased latency, missed cycles, jitter, potential instability. Detection: cycle time monitoring, latency measurement, jitter statistics. Distinction from attack: timing failures are typically systemic (all cycles affected) while delay attacks may target specific cycles.

**F6: Communication Failure.** The wireless link (NL-004) is disrupted, preventing clinician communication or telemetry. Effects: inability to adjust therapy, loss of diagnostic data. Detection: communication timeout, packet loss rate monitoring. Distinction from attack: communication failures affect both uplink and downlink symmetrically, while jamming may be directional.

**F7: Combined/Systemic Failure.** Multiple failure modes occur simultaneously, either cascading (one failure causes another) or independently. Effects: unpredictable, potentially catastrophic. Detection: correlation across multiple monitors. This is the failure mode most similar to a sophisticated attack, making it the hardest to distinguish from malicious action.

### 14.2 Failure-Aattack Distinction Matrix

| Feature | Sensor Failure | Sensor Attack | Controller Failure | Controller Attack |
|---|---|---|---|---|
| Onset speed | Gradual or sudden | Can be either | Sudden | Can be gradual |
| Frequency specificity | All bands | Typically targeted | N/A (no spectral effect) | N/A |
| Cross-channel correlation | Usually preserved | May be absent | N/A | N/A |
| Repeatability | Consistent (same fault) | Variable (attacker control) | Consistent | Variable |
| Response to open-loop | Fault persists | Attack may stop | Fault persists | Attack may stop |
| Forensic evidence | Hardware signatures | May leave no trace | Firmware logs | May leave protocol traces |

This matrix informs the VIREON validation framework's approach to failure-attack classification, implemented in the CL-008 benchmark (forensic analysis).
