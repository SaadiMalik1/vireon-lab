# NL-005: Closed-Loop System Security for Neurostimulators
# Part 2: Deep Analysis (Sections 15-28)

---

## Section 15: Sensor Spoofing Attacks

### 15.1 Attack Overview

Sensor spoofing is the most security-critical attack class for closed-loop neurostimulation because the controller is designed to trust its sensor input. Unlike general-purpose computing systems where input validation is a fundamental security principle, neural signals are inherently variable and lack a clear "expected" pattern that can be used for validation. The controller cannot simply reject unusual sensor data because unusual data may represent a genuine clinical event (e.g., a sudden increase in beta power due to stress or medication wearing off).

The attacker's objective in a sensor spoofing attack is to cause the controller to make incorrect stimulation decisions by presenting it with false neural data. The false data can cause two types of harmful outcomes: (a) overstimulation — the controller believes beta power is dangerously high and increases stimulation beyond the therapeutic range, and (b) understimulation — the controller believes beta power is adequately suppressed and reduces or eliminates stimulation, causing therapeutic failure.

### 15.2 Electromagnetic Signal Injection

The most direct sensor spoofing method is electromagnetic (EM) signal injection onto the sensing electrodes. The attacker generates an EM field at beta-band frequencies (13-30 Hz) using an external coil or antenna positioned near the patient. The induced voltage on the electrodes depends on the coupling coefficient, which is a function of distance, coil geometry, tissue properties, and electrode impedance.

The coupling can be modeled as a transformer: the attacker's coil is the primary, and the electrode-tissue interface is the secondary. The induced voltage V_induced = M * dI_attacker/dt, where M is the mutual inductance and I_attacker is the current in the attacker's coil. For practical distances (1-10 cm), the coupling is weak — the induced voltage is typically 1-100 uV, compared to genuine LFP beta oscillations of 10-100 uV. However, a dedicated attacker with a sufficiently powerful transmitter and optimized coil geometry can achieve coupling ratios that dominate the genuine signal.

The key challenge for the attacker is maintaining coherent injection across multiple control cycles. A single injection event that lasts one cycle may cause a momentary feature spike that the controller partially corrects on the next cycle. To have a sustained effect, the injection must be stable for at least several time constants of the controller's response (typically 500 ms to 2 s). This requires the attacker to maintain a stable EM field for this duration, which increases detection risk.

### 15.3 Data Injection via Firmware Exploitation

A more reliable (but harder to achieve) sensor spoofing method exploits firmware vulnerabilities (NL-003) to directly modify the sensor data buffer. If the attacker can write arbitrary values to the buffer between the ADC and the DSP pipeline, they have complete control over the "sensed" neural data. This bypasses all physical coupling limitations — the injected values can be any number the attacker chooses.

The firmware attack surface for sensor data injection includes: (a) buffer overflow in the ADC driver that allows overwriting the sample buffer, (b) DMA channel misconfiguration that redirects data from an attacker-controlled source, (c) pointer corruption in the DSP pipeline that causes it to read from the wrong memory region, and (d) direct memory write through debug interface (JTAG/SWD) if not properly disabled in production.

For VIREON simulation purposes, we model firmware-based sensor injection as direct modification of the sensed beta power value before it reaches the controller. This abstracts away the specific exploitation mechanism and focuses on the control-theoretic effect.

### 15.4 Spoofing Detection via Physiological Plausibility

Detecting sensor spoofing requires distinguishing between genuine neural variability and injected signals. The VIREON validation framework uses four physiological plausibility checks:

1. **Rate-of-change limit:** Genuine beta power changes with a time constant of at least 50-100 ms (neural response to any stimulus, including pathological events). A step change in beta power that occurs in a single control cycle (10 ms) is physiologically impossible and indicates injection. The VIREON detector flags any feature change that exceeds d(beta)/dt_max = 2 * sigma_natural / T, where sigma_natural is the natural beta variability and T is the sample period.

2. **Spectral shape consistency:** Genuine beta oscillations have a characteristic spectral shape — a relatively narrow peak at 18-22 Hz with 1/f roll-off on either side. An EM injection at a single frequency produces a sharp spectral line that is inconsistent with this shape. The VIREON detector computes the spectral kurtosis (a measure of peak sharpness) and flags values that exceed the physiological range.

3. **Cross-channel correlation:** In multi-contact electrode configurations, beta power on adjacent contacts is typically correlated (r > 0.5) because they sense overlapping neural populations. An injection that appears on only one contact is suspicious. The VIREON detector computes the cross-channel correlation coefficient and flags low-correlation events.

4. **High-frequency content:** EM injection at beta frequencies often produces harmonics at 2x, 3x the fundamental frequency. Genuine neural oscillations do not produce harmonics (the neural response is not linear enough to create clean harmonics). The VIREON detector checks for energy in harmonic bands (26-60 Hz for beta harmonics) that correlates with beta power.

### 15.5 Adversarial Sensor Spoofing

A sophisticated attacker aware of these detection mechanisms can craft spoofing signals that evade them. The adversarial spoofing problem can be formulated as an optimization: find the injected signal x_inject that maximizes the controller's error (driving it toward the attacker's objective) while minimizing the detection metric. This is an adversarial ML problem (previewed here, detailed in NL-006) that requires the attacker to have a model of the detection algorithm.

For example, to evade the rate-of-change detector, the attacker ramps the injected signal gradually, increasing it by at most d(beta)/dt_max per cycle. To evade the spectral shape detector, the attacker uses a broadband beta-band signal instead of a narrowband tone. To evade the cross-channel detector, the attacker injects correlated signals on multiple channels. Each evasion technique reduces the attack's effectiveness (the ramp is slower than a step, the broadband signal is less efficient than a tone) but may still achieve the attacker's objective if sustained long enough.

---

## Section 16: Controller Parameter Manipulation

### 16.1 Attack Overview

Controller parameter manipulation directly modifies the PI controller's gains (Kp, Ki) or setpoint to alter the closed-loop system's behavior. This attack targets AS-3 (Controller Surface) and can be achieved through wireless protocol exploitation (NL-004 — sending a parameter modification command), firmware exploitation (NL-003 — modifying parameter memory), or a combination of both.

The impact of parameter manipulation is most naturally analyzed through control theory. Changing Kp and Ki shifts the closed-loop poles, potentially moving them toward or across the unit circle. The attacker can target several objectives: instability (poles outside unit circle), sluggish response (poles close to z=1), oscillatory response (poles with large imaginary part), or incorrect steady-state (modified setpoint).

### 16.2 Gain Manipulation and Stability Boundary

For the canonical closed-loop DBS system with first-order plant G(z) = K*(1-a)/(z-a) where a = exp(-T/tau), and PI controller C(z) = ((Kp+Ki*T)*z - Kp)/(z-1), the closed-loop characteristic equation is:

    z^2 + (Kp*(1-a) - 1 - a)*z + (a - Kp*(1-a) + Ki*T*K*(1-a)) = 0

The stability boundary in the (Kp, Ki) plane is obtained by substituting z = exp(j*theta) for theta in [0, pi] and solving for the (Kp, Ki) pairs that place poles on the unit circle. This boundary divides the parameter space into a stable region (poles inside unit circle) and an unstable region (poles outside unit circle).

For representative parameters (K = 1, a = 0.951, T = 10 ms), the stability boundary is approximately: Ki < 10 * (1 + a - Kp*(1-a)) / (T*K*(1-a)). For Kp = 0.05 and T = 0.01, the maximum stable Ki is approximately 10.0 — well above the clinical tuning of 0.005. This means the clinical tuning is very conservative, and a significant gain increase is needed to cause instability. However, an attacker who sets Kp = 0.5 and Ki = 5.0 would place the poles near the unit circle, causing sustained oscillations that are clinically harmful even if technically "stable" (bounded).

### 16.3 Setpoint Modification

Changing the therapeutic setpoint (r[n]) is a simpler but equally dangerous attack. The setpoint defines the target beta power that the controller tries to maintain. In clinical use, the setpoint is calibrated by the clinician based on the patient's individual neural signature and therapeutic response. An incorrect setpoint causes the controller to pursue the wrong objective.

If the attacker sets the setpoint higher than the natural beta power (e.g., setpoint = +10 dB when natural beta is 0 dB), the controller interprets the natural state as "below target" and increases stimulation to raise beta power — the opposite of therapeutic intent. This is an insidious attack because the controller is functioning correctly according to its programming; it is pursuing a wrong objective.

If the attacker sets the setpoint equal to the current beta power, the error is zero and the controller takes no action — effectively disabling closed-loop operation without triggering any alarm (since the controller correctly perceives that the target is achieved). This is the "setpoint tracking" attack mentioned in the attack tree (Section 13, C3).

### 16.4 Anti-Windup and Rate Limit Manipulation

Disabling anti-windup protection (Section 5.3) allows the integral term to accumulate without bound when the actuator saturates. The attack proceeds in three phases: (1) trigger saturation by spoofing extreme sensor data or modifying the setpoint, (2) allow the integrator to wind up over multiple cycles (10-100 cycles, depending on Ki), (3) remove the trigger and watch the wound-up integrator cause extended overstimulation.

Modifying the rate limit has two attack modes. Increasing the rate limit (or removing it entirely) allows the controller to make rapid stimulation changes, which can cause patient discomfort and increase the risk of tissue damage from rapid current transitions. Decreasing the rate limit to zero freezes the controller output, preventing any adaptation — equivalent to switching to open-loop mode without the clinician's knowledge.

### 16.5 Detection of Parameter Manipulation

Detecting controller parameter manipulation requires independent verification of the parameters. The VIREON validation framework implements: (a) parameter checksum — each parameter has a CRC that is verified by the safety monitor, (b) parameter range check — Kp, Ki, and setpoint must be within clinician-programmed bounds, (c) behavioral consistency — if the parameters change, the controller's behavior should change in a predictable way; sudden behavioral changes without corresponding parameter changes suggest tampering, (d) dual-storage — critical parameters are stored in two independent memory locations with cross-checking.

---

## Section 17: Setpoint Modification Attacks

### 17.1 The Setpoint as Security-Critical Parameter

The therapeutic setpoint is arguably the most security-critical single parameter in a closed-loop neurostimulation system. It defines the control objective and implicitly encodes the clinician's therapeutic intent. An incorrect setpoint causes the controller to pursue the wrong objective while functioning correctly in every other respect — the stimulation is adjusted appropriately, the safety limits are respected, the monitor sees no anomalies. The attack is invisible to all security mechanisms that do not explicitly validate the setpoint's clinical appropriateness.

In a clinical closed-loop DBS system, the setpoint represents the target beta-band power level. A typical setpoint might be -3 dB relative to the patient's medication-off baseline beta power, meaning the controller aims to reduce beta power by approximately 50%. The clinician determines this value through a calibration procedure that involves measuring the patient's baseline beta power, testing different stimulation levels, and observing the clinical response.

### 17.2 Setpoint Attack Taxonomy

**Positive setpoint shift:** Increasing the setpoint above the calibrated value causes the controller to accept more beta power before increasing stimulation. In the extreme, the setpoint can be set above the maximum physiological beta power, causing the controller to never increase stimulation — therapeutic failure. The clinical presentation is identical to a sensor failure that reports low beta power.

**Negative setpoint shift:** Decreasing the setpoint below the calibrated value causes the controller to be more aggressive in suppressing beta power. The patient receives more stimulation than therapeutically necessary, increasing side effects (dysarthria, paresthesia, mood changes). In the extreme, the setpoint can be set to -infinity, causing the controller to maximize stimulation.

**Setpoint oscillation:** Rapidly alternating the setpoint between high and low values causes the controller to oscillate between under- and over-stimulation. This is a denial-of-service attack that makes therapy ineffective while potentially causing patient distress from the stimulation fluctuations.

**Setpoint tracking attack:** Dynamically adjusting the setpoint to match the current beta power, creating zero error. The controller remains in closed-loop mode (it does not switch to open-loop) but takes no action. This is stealthier than forcing open-loop mode because the system appears to be functioning normally. The clinical presentation is identical to the sensor spoofing attack that reports zero beta power, but the forensic evidence is different (setpoint is modified, not the sensor data).

### 17.3 Setpoint Integrity Verification

Verifying setpoint integrity requires authenticating the source of setpoint changes. In a secure system, the setpoint can only be modified through an authenticated clinician command (using the wireless protocol from NL-004). The firmware stores the setpoint in protected memory with a secure hash. The safety monitor independently computes a hash of the stored setpoint and compares it to the expected value.

For VIREON, the setpoint integrity check is a mandatory validation point. The CL-004 benchmark specifically tests setpoint modification detection by injecting unauthorized setpoint changes and verifying that the safety monitor detects them within the specified time window.

---

## Section 18: Delay Injection Attacks

### 18.1 Delay as a Stability Threat

Delay injection attacks increase the latency of the closed-loop feedback path, degrading the phase margin and potentially pushing the system into instability. As analyzed in Section 9.2, the phase margin loss due to additional delay d at frequency omega is PM_loss = omega * d. For typical closed-loop DBS parameters, even modest additional delays (20-50 ms) can reduce the phase margin to dangerously low levels.

The insidious property of delay attacks is that they do not modify any data or parameters — they only affect timing. Traditional security mechanisms (encryption, authentication, integrity checks) are designed to protect data, not timing. A delay attack can be implemented by any mechanism that slows down the processing pipeline, buffers data before delivering it, or disrupts the timing signals that coordinate the control loop.

### 18.2 Implementation Mechanisms

**Software buffering:** The attacker modifies the firmware to insert a buffer between the sensing and processing blocks (or between any two consecutive blocks). The buffer holds data for a specified number of cycles before releasing it, introducing a fixed delay. This is simple to implement but requires firmware modification (AS-2/AS-3).

**Computational overload:** The attacker triggers computationally expensive operations (complex DSP, memory-intensive operations) that compete with the control loop for CPU time. On a single-core Cortex-M4 without memory protection, a higher-priority task can preempt the control loop, introducing variable delay. This is an indirect delay attack that exploits RTOS scheduling.

**Timer manipulation:** The attacker modifies the hardware timer that drives the control loop's sampling and processing schedule. Changing the timer period directly changes the sampling rate (Section 9.4), which has stability implications beyond simple delay. On Cortex-M, the SysTick timer or a general-purpose timer (TIM2, TIM3) drives the control loop, and these can be reconfigured through register writes.

**Interrupt blocking:** The attacker disables or delays the control loop's timer interrupt, causing the control loop to miss one or more cycles. Each missed cycle effectively doubles the delay for that cycle. This is the most disruptive timing attack because it causes the delay to be an integer multiple of the cycle period, which can be particularly destabilizing for systems tuned assuming regular sampling.

### 18.3 Delay Attack Detection

Detecting delay attacks requires explicit timing monitoring that goes beyond the control loop's nominal timing. The VIREON validation framework specifies three detection layers:

1. **Cycle time monitoring:** Measure the actual time between consecutive control cycles and flag any deviation beyond a threshold (e.g., > 1 ms deviation from the nominal 10 ms). This detects timing manipulation but not software buffering (which preserves cycle timing while adding pipeline delay).

2. **Pipeline latency measurement:** Inject a timestamp at the sensing block input and measure when it appears at the actuation block output. This requires a dedicated timing path that bypasses the normal data pipeline. If the measured latency exceeds the expected value (sensing + processing + control + actuation), a delay attack is indicated.

3. **Phase margin estimation:** The most sophisticated detection method estimates the system's phase margin in real time by injecting small perturbations and measuring the response. A decreasing phase margin indicates increasing effective delay. This method directly measures the stability-relevant quantity but is computationally expensive and may itself perturb the control loop.

### 18.4 Delay Attack Impact on Stability

The impact of delay on stability depends on the relationship between the delay and the system's gain crossover frequency. The gain crossover frequency is the frequency at which the open-loop gain equals 1 (0 dB). At this frequency, the phase margin determines stability. Additional delay at the crossover frequency has maximum impact because it directly reduces the phase margin.

For a PI-controlled first-order system, the gain crossover frequency is approximately:

    omega_gc = sqrt(Ki * K / tau) (for Kp >> Ki*T)

With typical parameters (Ki = 0.005, K = 1, tau = 0.2 s), omega_gc = 0.158 rad/s (0.025 Hz). This is very low, meaning the system is relatively robust to delay. However, if the attacker first increases Ki (Section 16.2), the crossover frequency increases, and the same delay has a larger impact. This is an example of attack composition: combining controller manipulation with delay injection amplifies the overall effect.

---

## Section 19: Feedback Bypass and Open-Loop Forcing

### 19.1 Attack Overview

Feedback bypass attacks disrupt the feedback path, forcing the system to operate in open-loop mode or with a severed feedback connection. Without feedback, the controller cannot adapt to changes in the patient's neural state, and any errors in the stimulation parameters persist indefinitely. The attack can be implemented at multiple points in the loop: disabling the sensing block (no feedback signal), corrupting the feedback data path (feedback arrives but is wrong), or forcing the state machine into OPEN_LOOP mode.

### 19.2 Implementation Mechanisms

**Sensing disable:** The attacker disables the ADC, disconnects the electrode from the amplifier, or masks the sensing interrupt. The controller receives no new feature values and either holds its last output or switches to a default. If the controller holds its last output, the system continues with fixed stimulation — not inherently dangerous but therapeutically inadequate because it cannot respond to changing neural state.

**Data path corruption:** The attacker corrupts the memory region or register that carries the feature value from the processing block to the control block. The controller receives a fixed or slowly varying value that does not reflect the actual neural state. This is more insidious than sensing disable because the controller appears to be operating normally (it receives data, computes an error, adjusts stimulation) but the data is wrong.

**State machine forcing:** The attacker modifies the system state variable to OPEN_LOOP, causing the firmware to bypass the controller entirely and use fixed stimulation parameters. This requires firmware-level access but is simple to implement. The forensic evidence is clear (the state register shows OPEN_LOOP), making it easy to detect after the fact.

### 19.3 Detection and Response

Feedback bypass detection relies on monitoring the data flow through the feedback path. The VIREON framework specifies: (a) heartbeat monitoring — the processing block produces a "feature ready" signal every control cycle; if this signal is missing, the monitor detects feedback loss, (b) data freshness check — the monitor independently reads the sensor data (at lower resolution) and verifies that the controller's input is consistent, (c) behavioral monitoring — if the controller output stops changing for an extended period (more than N cycles) while the patient's clinical state is known to be variable, the monitor flags potential feedback loss.

The appropriate response to detected feedback bypass is to switch to a safe open-loop mode with clinician-specified default parameters. This is a controlled degradation that maintains some therapeutic benefit while alerting the clinician to the problem.

---

## Section 20: Adversarial Perturbation of Neural Feedback

### 20.1 Beyond Simple Spoofing

Simple sensor spoofing (Section 15) injects a false signal that directly represents the attacker's desired feature value. Adversarial perturbation is more subtle: the attacker injects a carefully crafted perturbation that, when processed by the DSP pipeline (NL-002), produces the desired effect on the extracted feature. The perturbation is optimized to maximize its impact on the control variable while minimizing its detectability by the sensor integrity checks (Section 7.2).

The distinction is important because the DSP pipeline is not transparent — it includes filtering, windowing, and spectral estimation that transform the raw signal in nonlinear ways (particularly windowing and log-compression of spectral estimates). A perturbation that looks small in the raw signal domain may be amplified by the processing pipeline, and vice versa. The adversarial perturbation approach explicitly accounts for this transformation.

### 20.2 Mathematical Formulation

Let x[n] be the genuine neural signal (length N window), and delta[n] be the attacker's perturbation. The perturbed signal is x_perturbed[n] = x[n] + delta[n]. The processing pipeline computes the feature value: f(x_perturbed) = beta_power_perturbed. The attacker's objective is to maximize some function of the resulting control error, subject to a constraint on the perturbation magnitude:

    max_delta  L(f(x + delta))  subject to  ||delta||_2 <= epsilon

Where L() is the loss function (e.g., the squared error between the perturbed feature and the attacker's target feature), and epsilon is the maximum perturbation magnitude (constrained by the attacker's injection capability).

This is a constrained optimization problem that can be solved using gradient-based methods if the processing pipeline is differentiable (or approximately differentiable). The gradient dL/d(delta) can be computed via the chain rule through the processing pipeline: dL/d(delta) = dL/df * df/dx_perturbed * dx_perturbed/d(delta) = dL/df * df/dx_perturbed. The term df/dx_perturbed is the Jacobian of the feature extraction with respect to the input signal.

### 20.3 Practical Considerations

In practice, the attacker faces several challenges. First, the attacker may not have a precise model of the DSP pipeline (filter coefficients, window function, spectral estimation method). Second, the genuine neural signal x[n] is not known to the attacker in real time (the attacker can only measure the electromagnetic field at the skin surface, which is a distorted version of the intracranial signal). Third, the optimization must be solved in real time (the perturbation must be computed within one control cycle).

Despite these challenges, adversarial perturbation attacks are feasible in simulation and may be feasible in practice with sufficient attacker capability. The key insight is that the perturbation does not need to be optimal — it only needs to be good enough to shift the controller's behavior in the desired direction. Even a suboptimal perturbation that shifts beta power estimation by 1-2 dB can cause clinically significant changes in stimulation over multiple control cycles.

### 20.4 Countermeasures

Defending against adversarial perturbation requires making the feature extraction pipeline robust to input perturbations. Approaches include: (a) randomized preprocessing — applying a random phase shift or time warp before feature extraction, making the optimization landscape non-stationary, (b) ensemble feature extraction — computing features using multiple different pipelines and comparing results, (c) input validation — checking the raw signal for anomalies (spectral shape, statistics) before processing, (d) adversarial training — training a detector on adversarially-perturbed signals to learn to recognize attack patterns.

---

## Section 21: Loop Instability Attacks

### 21.1 Oscillatory Instability

Oscillatory instability occurs when the closed-loop poles cross the unit circle, causing the system's response to grow (or sustain) oscillations. In neurostimulation, this manifests as the stimulation amplitude and the sensed beta power oscillating in antiphase: high stimulation suppresses beta, the controller sees low beta and reduces stimulation, low stimulation allows beta to increase, the controller sees high beta and increases stimulation, and the cycle repeats with growing amplitude.

The oscillation frequency is determined by the imaginary part of the unstable poles. For a second-order system, the oscillation frequency is approximately the angle of the pole in the z-plane divided by the sample period. For a pole at z = r * exp(j*theta) with r > 1, the oscillation frequency is theta / (2*pi*T) Hz. With T = 10 ms, a pole at theta = pi/4 (45 degrees) produces oscillations at 12.5 Hz — coincidentally in the beta band, which can create a confusing resonance effect.

### 21.2 Runaway Stimulation

Runaway stimulation occurs when the controller's output grows monotonically toward the maximum. Unlike oscillatory instability, runaway is a non-oscillatory divergence where the stimulation increases (or decreases) without bound. In practice, output clamping (Section 5.4) prevents true divergence, but the controller reaches and holds the maximum (or minimum) stimulation, which is clinically dangerous.

Runaway is typically caused by: (a) persistent positive error due to sensor spoofing or setpoint modification, (b) integral windup (Section 5.3), or (c) incorrect controller gains that shift the real pole outside the unit circle. The safety monitor detects runaway by checking whether the output has been at its limit for more than a specified duration (e.g., > 2 seconds at maximum stimulation triggers an alarm).

### 21.3 Instability Detection

The safety monitor detects instability by monitoring the stimulation output and the sensed feature for oscillatory behavior. Detection methods include:

- **Zero-crossing rate:** Count the number of times the stimulation output crosses its mean value per unit time. A high zero-crossing rate indicates oscillatory behavior. For a stable system, the output varies slowly; for an unstable system, it oscillates at the pole frequency.

- **Autocorrelation peak lag:** Compute the autocorrelation of the stimulation output and find the lag of the first peak. A well-defined peak at a specific lag indicates oscillation at the corresponding frequency. This method is more robust to noise than zero-crossing rate.

- **Power spectral density peak:** Compute the FFT of the stimulation output and check for a sharp peak. A stable controller produces a flat (or slowly varying) output spectrum; an unstable controller produces a spectral peak at the oscillation frequency.

- **Envelope growth rate:** Compute the envelope of the stimulation output and check whether it is growing. A growing envelope indicates true instability (pole magnitude > 1); a constant envelope indicates sustained oscillation (pole magnitude = 1).

### 21.4 Instability Severity Classification

VIREON classifies instability events by severity: Level 1 (marginally stable, poles near but inside unit circle, small oscillations that may be clinically tolerable), Level 2 (poles on unit circle, sustained oscillations, clinically significant stimulation fluctuations), Level 3 (poles outside unit circle, growing oscillations, immediate clinical risk). The safety monitor response depends on severity: Level 1 triggers increased monitoring, Level 2 triggers open-loop fallback, Level 3 triggers stimulation disable.

---

## Section 22: Protocol-Loop Interaction Attacks

### 22.1 How Wireless Protocol Affects the Control Loop

The wireless protocol (NL-004) provides the communication channel for clinician commands (parameter updates, mode changes) and device telemetry (neural data, stimulation logs, battery status). While the control loop operates autonomously (it does not require wireless communication to function), the wireless protocol affects the loop in several ways.

First, parameter updates arrive via the wireless protocol. If an attacker can inject unauthorized parameter changes (NL-004 WP-003, WP-004), these changes take effect in the control loop immediately (or at the next control cycle). The protocol's authentication and replay protection mechanisms directly determine the loop's resilience to remote parameter manipulation.

Second, the wireless protocol's latency and reliability affect how quickly the clinician can respond to anomalies detected by the device. If the device detects an instability event and sends a telemetry alert, but the wireless link is jammed or delayed, the clinician cannot intervene in time. The protocol's reliability mechanisms (acknowledgments, retransmissions) and the device's autonomous safety responses must be designed to handle communication failures.

Third, the protocol's energy consumption affects the control loop's duty cycle. If the wireless protocol consumes significant energy (e.g., due to an attack that forces frequent re-authentication or data transmission), the device may need to reduce control loop frequency to conserve battery, degrading therapeutic performance.

### 22.2 Specific Attack Scenarios

**Remote gain manipulation:** An attacker exploits the wireless protocol (NL-004) to send a SET_PARAMETERS command that modifies Kp and Ki. If the protocol's per-command authorization (NL-004 Section 11) does not properly restrict CLINICAL-level commands, the attacker can modify controller parameters. The CL-003 benchmark specifically tests this scenario.

**Replayed parameter change:** An attacker records a legitimate parameter update from a previous session and replays it. If the protocol's replay protection (NL-004 Section 9) is compromised, the replayed command modifies the controller parameters. The danger is that the replayed parameters may be inappropriate for the patient's current state (e.g., parameters from a different clinical configuration).

**Telemetry injection:** An attacker sends fake telemetry data that mimics a device alert, causing the clinician programming system to display incorrect information. While this does not directly affect the control loop, it can cause the clinician to take incorrect actions (e.g., reducing stimulation based on fake "overstimulation" alerts).

### 22.3 Protocol-Jitter Induced Loop Perturbation

Wireless communication activity can introduce electromagnetic interference (EMI) that affects the sensing electronics. When the implant transmits a telemetry packet, the RF power amplifier generates broadband noise that can couple into the sensing amplifier. This creates a correlation between wireless activity and sensing quality: during transmission, the sensed signal quality degrades.

An attacker who can trigger frequent transmissions (e.g., by sending repeated requests) creates periodic sensing degradation that perturbs the control loop. The perturbation is at the wireless communication rate, which may be much slower than the control loop rate, creating a low-frequency modulation of the control loop's effective gain.

---

## Section 23: Cross-Channel Closed-Loop Attacks

### 23.1 Multi-Channel Closed-Loop Systems

Advanced neurostimulation systems sense and stimulate on multiple channels simultaneously. For example, a closed-loop DBS system may sense beta power from two STN contacts (left and right) and independently control stimulation on each side. A responsive neurostimulation system for epilepsy may sense from 4 electrode contacts and deliver stimulation through any combination of them.

Multi-channel systems create additional attack surfaces: cross-channel attacks where the attacker exploits the interaction between channels. These attacks have no analog in single-channel systems and require understanding the inter-channel coupling dynamics.

### 23.2 Cross-Channel Coupling Exploitation

Neural populations recorded by different electrode contacts are not independent — they are coupled through anatomical connections (direct neural projections, shared input, common modulation). This coupling means that stimulation on one channel affects the sensed signal on other channels. The coupling strength and direction depend on the anatomical substrate.

In bilateral STN DBS, the left and right STN are not directly connected but share common cortical and cerebellar inputs. Stimulation on the left STN primarily affects left STN beta power but has a smaller effect (typically 5-15% coupling) on right STN beta power. An attacker who understands this coupling can launch a cross-channel attack: stimulate on one channel to modulate the sensed signal on another channel, creating a feedback path that bypasses the intended control architecture.

### 23.3 Channel Isolation and Validation

Defending against cross-channel attacks requires: (a) electrical isolation between sensing and stimulation circuits on different channels, (b) independent control loops for each channel with their own safety monitors, (c) cross-channel consistency checks (the sensed effect on a non-stimulated channel should be consistent with the known coupling model), (d) stimulation blanking on all channels when any channel is stimulating (to prevent cross-channel stimulation artifact).

---

## Section 24: Energy-Based Attacks on Closed-Loop Systems

### 24.1 Battery Drain as Attack Vector

Implantable neurostimulators have limited battery capacity (typically 100-3000 mAh depending on battery chemistry and device size). Closed-loop operation consumes more energy than open-loop because of the continuous sensing, processing, and control computation. The wireless protocol (NL-004) adds additional energy consumption for communication.

An attacker who can increase the device's energy consumption can drain the battery prematurely, causing the device to shut down or switch to a low-power mode with reduced or no therapy. Energy-based attacks are denial-of-service attacks that exploit the finite energy resource of implantable devices.

### 24.2 Energy Consumption Model for Closed-Loop

The closed-loop system's energy consumption has several components:

- **Sensing energy:** ADC operation, amplifier bias, and signal buffering. Typically 10-50 uW continuous.
- **Processing energy:** DSP computation per control cycle. Typically 1-10 uJ per cycle at 100 Hz = 100-1000 uW average.
- **Control energy:** PI controller computation. Negligible (< 1 uW) compared to processing.
- **Actuation energy:** Stimulation pulse delivery. Dominates total consumption. Typically 10-100 uJ per pulse at 100-200 Hz = 1-20 mW average.
- **Wireless energy:** MICS transceiver operation (NL-004 EnergyModel). RX: 2.5 uJ/packet, TX: 15 uJ/packet. At 10 packets/sec: 175 uW average.

In closed-loop mode, the total average power is typically 1-20 mW, depending on the stimulation parameters. The battery life is: Life = Battery_Capacity / Average_Power. For a 500 mAh battery at 3.7 V (6.66 Wh) and 10 mW average: Life = 666 hours = 27.7 days. This is the absolute upper bound; actual battery life is typically 3-15 years for modern DBS devices due to aggressive duty cycling.

### 24.3 Energy Attack Scenarios

**Forced maximum stimulation:** By spoofing sensor data to indicate maximum pathological beta, the attacker causes the controller to deliver maximum stimulation. Maximum stimulation consumes 5-10x more energy than typical therapeutic stimulation, reducing battery life proportionally.

**Communication flooding:** Repeatedly triggering wireless communication (e.g., through replayed session requests, fake telemetry requests, or protocol-level DoS from NL-004 WP-006) forces the transceiver to operate continuously. The MICS transceiver at continuous operation consumes 10-50 mW — comparable to or exceeding the stimulation energy.

**Sensing overload:** Forcing the sensing block to operate at maximum sampling rate (e.g., by modifying timer registers) increases sensing energy consumption. While the absolute increase is modest (10-50 uW), it adds to the total and can be combined with other attacks.

The VIREON EnergyModel tracks cumulative energy consumption and flags when the projected battery life falls below a threshold (e.g., < 24 hours remaining triggers a low-battery alert). The CL-005 benchmark tests energy-based attacks.

---

## Section 25: Safety Monitor Evasion Techniques

### 25.1 Monitor Evasion Taxonomy

The safety monitor is the last line of defense for closed-loop neurostimulation. Evading the monitor is a prerequisite for any sustained attack that would otherwise be detected and countered. Monitor evasion techniques are classified by the mechanism used:

**E1: Monitor disable.** The attacker disables the monitor entirely through firmware modification. This is the most direct approach but also the most detectable — firmware integrity checks (secure boot, hash verification) can detect unauthorized firmware modifications.

**E2: Threshold elevation.** The attacker increases the monitor's detection thresholds so that attack-induced anomalies fall below the alarm level. For example, increasing the instability detection threshold from "oscillation amplitude > 0.5 mA" to "oscillation amplitude > 5 mA" allows the attacker to cause 4.9 mA oscillations without detection. This requires firmware-level access to modify the threshold parameters.

**E3: Data poisoning.** The attacker feeds false data to the monitor while attacking the control loop. If the monitor independently reads the sensor data (Level 2 independence, Section 10.2), the attacker must poison both the control path and the monitor's independent sensing path simultaneously. This requires multi-channel compromise.

**E4: Timing desynchronization.** The attacker causes the monitor to check data that is delayed relative to the control loop's data. The monitor sees "normal" (stale) data while the control loop operates on corrupted (current) data. This exploits timing vulnerabilities in the monitor's sampling schedule.

**E5: Alarm fatigue.** The attacker triggers repeated false alarms to cause the clinician to disable or ignore the alarm system. This is a social engineering attack that exploits the human element of the safety chain. It requires repeated triggering of the alarm without causing actual danger (to avoid triggering emergency responses that cannot be dismissed).

### 25.2 Multi-Vector Evasion

A sophisticated attacker may combine multiple evasion techniques. For example: use E4 (timing desynchronization) to allow a brief attack window, use E2 (threshold elevation) to allow a larger attack within that window, and use E5 (alarm fatigue) to prevent clinician intervention when the attack is eventually detected. This multi-vector approach significantly raises the bar for defense and is the scenario that VIREON's highest-severity benchmarks (CL-006, CL-008) are designed to test.

### 25.3 Monitor Hardening Strategies

To counter monitor evasion, VIREON recommends: (a) hardware-enforced monitor operation — the monitor's timer cannot be modified by firmware, (b) random monitor scheduling — the monitor checks at slightly randomized intervals to prevent timing desynchronization attacks, (c) multi-metric correlation — the monitor uses multiple independent metrics and flags when they disagree, (d) monotonic counters — each alarm type has a counter that increments and never resets; a sudden spike in any counter is suspicious even if individual alarms are dismissed, (e) clinician-side anomaly detection — the external programmer system monitors telemetry for patterns that indicate monitor evasion (e.g., suspiciously consistent reports, missing alarm events).

---

## Section 26: Closed-Loop Attack Detection

### 26.1 Detection Architecture

Closed-loop attack detection operates at three levels, each with different latency and confidence:

**Level 1: Per-cycle checks.** Executed every control cycle (10 ms). Fast but low-confidence checks including: feature range check, output range check, rate-of-change check, NaN/Infinity check. These checks catch gross anomalies but can be evaded by sophisticated attacks.

**Level 2: Multi-cycle analysis.** Executed over windows of 10-100 cycles (100 ms - 1 s). Medium-latency, medium-confidence checks including: zero-crossing rate (instability detection), feature statistics (mean, variance, kurtosis), cross-channel consistency, energy consumption trend. These checks detect trends that are invisible to per-cycle checks.

**Level 3: Long-term pattern analysis.** Executed over windows of 100-1000 cycles (1-10 s). Slow but high-confidence checks including: stability margin estimation, controller parameter consistency, behavioral pattern analysis, forensic correlation. These checks provide the highest confidence but are too slow to prevent immediate harm.

### 26.2 Statistical Detection Methods

The VIREON detection framework uses statistical methods that distinguish between normal neural variability and attack-induced perturbations:

**Change-point detection:** The CUSUM (cumulative sum) algorithm detects sustained shifts in the mean of the feature value. A genuine clinical event (e.g., medication wearing off) causes a gradual shift over minutes; an attack may cause a sudden shift in seconds. The CUSUM detection time depends on the shift magnitude relative to the natural variability — small, slow attacks are harder to detect than large, fast attacks.

**Anomaly detection:** The controller's behavior (output sequence) is compared against a model of normal behavior. Deviations from the model indicate potential attacks. The model can be a simple statistical model (mean and covariance of the output) or a more complex learned model (autoencoder, one-class SVM, previewed in NL-006).

**Consistency checking:** The relationship between the sensed feature, the controller output, and the predicted next-cycle feature is checked for consistency. In a properly functioning loop, increasing stimulation should decrease beta power (after the neural delay). If the controller increases stimulation but beta power also increases, something is wrong — either the sensor is spoofed, the controller parameters are wrong, or the neural response has fundamentally changed.

### 26.3 False Alarm Management

A fundamental tension in closed-loop attack detection is between sensitivity (detecting real attacks) and specificity (avoiding false alarms). False alarms are dangerous in neurostimulation because switching to open-loop mode or disabling stimulation due to a false alarm deprives the patient of therapy. An attacker can exploit false alarm sensitivity by triggering repeated false alarms (alarm fatigue, E5) to condition the clinician to ignore genuine alarms.

VIREON manages false alarms through: (a) graduated response — low-confidence detections trigger increased monitoring rather than immediate intervention, (b) hysteresis — the detection threshold is higher for transitioning from normal to alarm than for transitioning from alarm to normal, (c) confidence scoring — each detection produces a confidence score, and intervention is triggered only when the score exceeds a high threshold, (d) clinician-configurable sensitivity — the clinician can adjust the trade-off between sensitivity and specificity based on the patient's risk profile.

---

## Section 27: Countermeasure Architecture

### 27.1 Defense-in-Depth for Closed-Loop

The countermeasure architecture for closed-loop neurostimulation follows the defense-in-depth principle with five layers:

**Layer 1: Prevention.** Prevent attacks from reaching the control loop. Includes: wireless protocol security (NL-004), firmware security (NL-003), physical shielding of the sensing electronics. Prevention is the strongest defense but cannot be perfect — the attacker may find a vulnerability in any layer.

**Layer 2: Input Validation.** Validate all inputs to the control loop before they affect the output. Includes: feature range checks, rate-of-change limits, NaN/Infinity detection, spectral consistency checks. Input validation catches attacks that bypass Layer 1 but have obvious anomalies.

**Layer 3: Behavioral Monitoring.** Monitor the control loop's behavior for anomalies that indicate attack. Includes: instability detection, sensor anomaly detection, energy consumption monitoring, timing monitoring. Behavioral monitoring catches attacks that produce subtle input anomalies but create detectable output patterns.

**Layer 4: Safety Monitor.** Independent monitoring with authority to force safe states. Includes: stimulation limit enforcement, stability monitoring, sensor integrity verification, timing verification. The safety monitor is the backstop that catches attacks that evade Layers 1-3.

**Layer 5: Clinician Oversight.** The human clinician provides the final layer of defense through telemetry review, alarm response, and clinical judgment. The clinician can detect attacks that no automated system can — for example, recognizing that the patient's symptoms are inconsistent with the reported device behavior.

### 27.2 Secure Controller Architecture

The controller itself should be designed with security as a first-class requirement. VIREON defines a secure controller architecture with these properties:

- **Immutable core algorithm:** The PI controller's difference equation is implemented in read-only memory (flash with write protection). The algorithm cannot be modified without a firmware update with full authentication chain.

- **Protected parameter storage:** Controller parameters (Kp, Ki, setpoint) are stored in MPU-protected memory regions with hardware write-protection. Modification requires unlocking the MPU region, which triggers a secure boot verification.

- **Redundant computation:** The control output is computed by two independent code paths (primary and secondary). If the results disagree by more than a tolerance, the monitor is alerted. The secondary path uses a simplified but equivalent algorithm.

- **Bounded state:** The controller's internal state (integral term) is bounded and monitored. Integral windup is prevented by conditional integration (Section 5.3). The integral value is checked every cycle against a maximum.

- **Deterministic timing:** The controller runs at a fixed priority in the RTOS with a dedicated timer interrupt. Other tasks cannot preempt the controller. The cycle time is measured and logged every cycle.

### 27.3 Resilient Closed-Loop Design

Beyond preventing attacks, the closed-loop system should be designed to degrade gracefully under attack. Resilient design principles include:

- **Graceful degradation:** When an anomaly is detected, the system transitions through progressively safer modes (closed-loop with increased monitoring → open-loop with safe defaults → stimulation off → emergency shutdown) rather than jumping directly to the most severe response.

- **Therapeutic continuity:** Even during a detected attack, the system should attempt to maintain some therapeutic benefit. Switching to open-loop mode with safe default parameters is preferable to disabling stimulation entirely (unless the attack directly threatens tissue safety).

- **Forensic data preservation:** When an anomaly is detected, the system preserves a detailed forensic record (sensor data, control outputs, monitor alerts, timing data) for post-incident analysis. This record is stored in protected memory that survives power cycles.

- **Rapid recovery:** After an attack is resolved (e.g., the attacker's signal is removed, the compromised parameter is restored), the system should be able to resume closed-loop operation quickly. The controller's integral term should be reset to a safe value (not carried over from the attack period) and the system should undergo a brief re-calibration before resuming adaptive control.

---

## Section 28: Formal Verification of Loop Security

### 28.1 Why Formal Methods for Closed-Loop

Formal verification provides mathematical proof that a system satisfies specified properties under all possible inputs and states. For closed-loop neurostimulation, formal verification can prove that: (a) the controller output is always within safe limits, regardless of the sensor input (bounded-input bounded-output property), (b) the closed-loop system is stable for all parameter values within the specified range, (c) the safety monitor detects all specified anomaly types within the specified time window, (d) no sequence of state transitions can lead to a dangerous state without triggering a monitor response.

These properties cannot be fully verified through testing alone — the input space is too large (continuous-valued neural signals, parameter combinations, timing variations). Formal methods provide exhaustive coverage that testing cannot.

### 28.2 Model Checking for Closed-Loop Properties

Model checking verifies temporal logic properties of finite-state systems. For closed-loop neurostimulation, the controller and monitor can be abstracted to a finite-state model by discretizing the continuous-valued signals into a finite set of regions. The property to verify is expressed in Linear Temporal Logic (LTL) or Computation Tree Logic (CTL).

Example LTL property: "If the stimulation amplitude exceeds the safety threshold, then the safety monitor will switch to safe mode within 10 control cycles."

    G (stim > threshold -> F[<=10] (state == SAFE_MODE))

Where G is "globally" (always), F is "finally" (eventually), and [<=10] is "within 10 steps."

### 28.3 Reachability Analysis

Reachability analysis determines whether a dangerous state is reachable from any initial state through any sequence of transitions. For the closed-loop system, dangerous states include: stimulation exceeding limits, controller output diverging, monitor being disabled while stimulation is active, and the system being in an unstable oscillatory state.

The state space for reachability analysis includes: the controller state (integral term, error), the plant state (neural activity), the monitor state (alert level, last check results), and the system state (mode, timing). This state space is continuous, so reachability analysis requires abstraction (e.g., interval arithmetic, polyhedral overapproximation).

### 28.4 VIREON Formal Verification Integration

The VIREON validation framework integrates formal verification as a complementary approach to simulation-based testing. The CL benchmarks (Part 3) are designed to be verifiable both through simulation (labs) and through formal methods (reachability analysis). The formal verification provides stronger guarantees for specific properties, while the simulation-based benchmarks provide evidence for properties that are difficult to formalize (e.g., adversarial perturbation robustness).

For the VIREON digital twin, the formal verification component proves properties of the controller and monitor under the assumption that the plant model is correct. The digital twin simulation tests the system under more realistic (but less exhaustive) conditions that include plant model uncertainty, noise, and timing variations.

The combination of formal verification and simulation provides the highest assurance level for closed-loop neurostimulator security — formal methods prove that the system is correct for the modeled threats, and simulation demonstrates that the system behaves correctly under realistic conditions that may not be fully captured by the formal model.
