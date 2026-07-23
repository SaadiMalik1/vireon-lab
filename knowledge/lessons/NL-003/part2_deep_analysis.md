# NL-003: Neurostimulator Firmware Architecture and Security (Part 2)

## 9. DSP Engine Firmware Implementation

### 9.1 From Algorithm to Firmware

The DSP algorithms described in NL-002 (filtering, feature extraction, artifact detection) must be implemented in firmware that runs on the IPG's MCU. This translation from mathematical algorithm to C code running on a Cortex-M4F involves trade-offs that affect both performance and security.

**Fixed-point vs. floating-point:** The Cortex-M4F includes a hardware floating-point unit (FPU) that enables single-precision (32-bit float) arithmetic at nearly the same speed as integer arithmetic. However, floating-point has security-relevant properties:

- **Non-determinism:** Floating-point operations are not associative (a + b + c may not equal a + (b + c)). Different compiler optimization levels may reorder operations, producing slightly different results. This non-determinism can cause the same signal to produce slightly different feature values depending on compiler flags — a reproducibility concern for VIREON's validation framework.
- **Special values:** NaN, infinity, and denormalized numbers can propagate through computations and produce unexpected results. A firmware vulnerability that produces a NaN in the band power computation (e.g., 0/0 from a zero-variance segment) could cause the closed-loop controller to make incorrect decisions. Mitigation: check for NaN/infinity before using computed values, and enable the Cortex-M FPU's flush-to-zero mode for denormals.
- **Side channels:** Floating-point operations on some Cortex-M4 implementations have timing that depends on operand values (e.g., denormals take longer). This creates a timing side-channel that could leak information about signal values.

**Fixed-point arithmetic** (using integer types with implicit scaling) avoids these issues but requires careful manual management of scaling, overflow, and precision. In safety-critical code paths, many manufacturers prefer fixed-point because its behavior is fully deterministic and its overflow behavior is well-defined (saturating or wrapping).

### 9.2 FIR Filter Firmware Implementation

The bandpass filter from NL-002 (used for beta-band extraction) is implemented in firmware as a direct-form FIR filter:

```c
// Simplified FIR filter implementation for beta-band extraction
// 4th-order Butterworth bandpass, 13-30 Hz, Fs=250 Hz
// Converted to FIR via impulse response truncation (51 taps)

#define FIR_TAPS 51
const int16_t fir_coefficients[FIR_TAPS] = { /* ... precomputed ... */ };
int32_t fir_delay_line[FIR_TAPS];  // Q15 format, allocated in dedicated SRAM region

// Called from DSP task at 250 Hz (every 4 ms)
int32_t fir_filter(int16_t input_sample) {
    int32_t acc = 0;
    int32_t input_q15 = (int32_t)input_sample << 15;  // Convert to Q15
    
    // Shift delay line
    for (int i = FIR_TAPS - 1; i > 0; i--) {
        fir_delay_line[i] = fir_delay_line[i-1];
    }
    fir_delay_line[0] = input_q15;
    
    // Compute output
    for (int i = 0; i < FIR_TAPS; i++) {
        // Q15 * Q15 = Q30, accumulate in Q30
        acc += (int32_t)fir_coefficients[i] * fir_delay_line[i];
    }
    
    // Convert Q30 back to Q15 with rounding
    return (acc + (1 << 14)) >> 15;
}
```

**Security vulnerabilities in this implementation:**

1. **Delay line overflow:** `fir_delay_line[i] = fir_delay_line[i-1]` copies values without bounds checking. If the function is called from an ISR (which can interrupt itself on Cortex-M), the delay line can be corrupted by a reentrant call. Mitigation: make the function non-interruptible (disable interrupts during execution) or use double-buffering.

2. **Accumulator overflow:** The accumulator `acc` is 32 bits (Q30). With 51 taps and Q15 inputs, the maximum possible accumulator value is 51 * 32767 * 32767 = 54.7 billion, which exceeds the 32-bit signed range (2.1 billion). This WILL overflow for large-amplitude inputs, producing incorrect results. Mitigation: use 64-bit accumulator (`int64_t acc`) or scale the coefficients to prevent overflow.

3. **Coefficient tampering:** The coefficients are stored in flash as `const`. If an attacker modifies flash (through a firmware exploit), they can change the filter's frequency response. For example, widening the passband to include 50 Hz powerline interference would cause the beta power estimate to be contaminated by line noise. VIREON should verify coefficient integrity at runtime.

4. **Timing side-channel:** The filter execution time depends on the input value if the accumulator overflows and triggers a hardware exception (which takes additional cycles). An attacker who can measure the filter's execution time (through a timing side-channel) can infer information about the input signal values.

### 9.3 FFT Firmware Implementation

The FFT is the most computationally intensive operation in the DSP pipeline. On a Cortex-M4F, a 256-point complex FFT takes approximately 5,000-15,000 cycles (20-60 us at 250 MHz). The CMSIS-DSP library provides optimized FFT implementations that use the hardware FPU and SIMD instructions.

**Security implications of FFT implementation:**

- **Input validation:** The FFT operates on a buffer of samples. If the buffer contains uninitialized data (e.g., due to a race condition where the DMA hasn't finished filling the buffer when the FFT starts), the output will be garbage. The DSP task must verify that the buffer is ready before starting the FFT.

- **Windowing function storage:** The window function (Hann, Hamming) is typically stored as a lookup table. If the table is in modifiable memory (SRAM), an attacker can corrupt it, changing the spectral properties of the output. This would affect all downstream features and could mask or create attack artifacts in the spectral domain.

- **Bit-reversal permutation:** The FFT algorithm requires bit-reversal permutation of either the input or output. This permutation is implemented as a sequence of memory accesses with specific addressing patterns. An attacker who can observe the memory access pattern (through a cache side-channel) can infer the FFT size and structure.

### 9.4 DSP Firmware Security Checklist

VIREON should verify the following properties of the DSP firmware:

| Check | Method | Severity if Failed |
|---|---|---|
| No accumulator overflow | Static analysis + boundary testing | High — incorrect features |
| No reentrant calls to filter functions | Audit call graph from ISRs | High — state corruption |
| Coefficients in read-only memory | Disassembly verification | Medium — filter manipulation |
| Window function in read-only memory | Disassembly verification | Medium — spectral manipulation |
| NaN/infinity handling | Inject NaN inputs, verify behavior | High — control loop corruption |
| Deterministic output for same input | Repeatability testing | Medium — reproducibility failure |
| Execution time bounded | Worst-case execution time analysis | Medium — timing side-channel |

## 10. Closed-Loop Controller Firmware

### 10.1 Controller Architecture

The closed-loop controller is the firmware component that reads DSP features and computes stimulation parameters. It implements the control algorithm that adapts stimulation to the patient's neural state in real time.

```
DSP Features          Controller          Stimulation
(band power,  ──────> │  Setpoint ────────> │  Parameters
 Hjorth, etc.)        │  Error = SP - PV   │  (amplitude,
                      │  Output = f(Error)  │   frequency, PW)
                      │                     │
                      │  Safety Limits ─────>│  Clamped output
                      └─────────────────────┘
```

### 10.2 Control Algorithm Implementation

The most common control algorithm for closed-loop DBS is a proportional-integral (PI) controller:

```c
// Closed-loop PI controller for adaptive DBS
// Input: beta_band_power (from DSP task)
// Output: stimulation_amplitude (to stimulation task)

typedef struct {
    float setpoint;          // Target beta power
    float kp;                // Proportional gain
    float ki;                // Integral gain
    float integral_state;    // Accumulated error
    float output_min;        // 0.0 mA
    float output_max;        // 7.0 mA (safety limit)
    float integral_max;      // Anti-windup limit
    uint32_t last_update_ms; // For derivative computation
} PIController;

float pi_update(PIController *ctrl, float process_variable, uint32_t now_ms) {
    float error = ctrl->setpoint - process_variable;
    
    // Integrate with anti-windup
    ctrl->integral_state += error * 0.01;  // dt = 10ms
    if (ctrl->integral_state > ctrl->integral_max) {
        ctrl->integral_state = ctrl->integral_max;  // Clamp
    } else if (ctrl->integral_state < -ctrl->integral_max) {
        ctrl->integral_state = -ctrl->integral_max;
    }
    
    // PI output
    float output = ctrl->kp * error + ctrl->ki * ctrl->integral_state;
    
    // Clamp to safety limits
    if (output > ctrl->output_max) output = ctrl->output_max;
    if (output < ctrl->output_min) output = ctrl->output_min;
    
    return output;
}
```

**Security vulnerabilities in this implementation:**

1. **Setpoint manipulation:** The `setpoint` value determines the target beta power. If an attacker can modify this value (through firmware access or a command injection attack that writes to the controller's memory), they can change the controller's behavior. Setting the setpoint to zero would cause the controller to maximize stimulation (since error = 0 - PV = -PV, always negative, integral winds up negatively, output goes to maximum). Setting the setpoint very high would minimize stimulation.

2. **Gain manipulation:** The proportional and integral gains (`kp`, `ki`) determine the controller's responsiveness. If an attacker increases `kp`, the controller becomes more aggressive — potentially causing rapid stimulation oscillations. If `ki` is increased, the integral term dominates, causing slow drift and eventual saturation.

3. **Integral windup attack:** The anti-windup limit (`integral_max`) prevents the integral from growing unboundedly. If an attacker sets `integral_max` to a very large value (or disables anti-windup), a sustained error (caused by the attacker manipulating the beta power estimate) will cause the integral to wind up to a large value, and when the error reverses, the controller will overshoot dramatically.

4. **Parameter injection via command:** If the wireless command parser allows modification of controller parameters without adequate authorization and validation, an attacker can directly control the closed-loop behavior. Even if parameter modification requires authorization, a session hijacking attack (compromising the pairing secret) provides the necessary authorization.

### 10.3 Controller Task Timing

The closed-loop controller runs as a periodic RTOS task. The task period (control loop rate) is a critical design parameter:

- **Too fast (e.g., 1 kHz):** The controller reacts to every fluctuation in the beta power estimate, including noise. This causes high-frequency stimulation modulation that may be clinically ineffective and may accelerate battery drain.
- **Too slow (e.g., 0.1 Hz):** The controller cannot respond to rapid changes in neural state (e.g., a movement-related beta burst). The patient loses the benefit of adaptive stimulation.
- **Typical:** 1-10 Hz for closed-loop DBS, matching the timescale of beta-band dynamics.

**Security implication:** The controller task period must be consistent with the feature extraction window (NL-002 Section 7.2). If the DSP produces a new band power estimate every second, the controller should run at approximately 1 Hz. If the controller runs faster than the feature update rate, it will make decisions based on stale features — a timing mismatch that an attacker could exploit.

### 10.4 State Machine for Therapy Modes

The closed-loop controller typically implements a state machine that governs therapy modes:

```
         ┌──────────┐
         │  INIT     │
         │  (boot)   │
         └────┬─────┘
              │ Self-test pass
              v
         ┌──────────┐     Parameter     ┌──────────┐
         │  IDLE     │ <──modification── │ OPEN_LOOP │
         │  (no     │                   │  (fixed  │
         │  stim)   │                   │  params) │
         └────┬─────┘                   └────┬─────┘
              │ Start command                │ Enable CL
              v                              v
         ┌──────────┐     Disable CL     ┌──────────┐
         │  STIM_ON │ ───────────────>   │ CLOSED   │
         │  (simple)│                   │  _LOOP   │
         └──────────┘                   │  (adaptive)│
                                        └──────────┘
```

**Security implication:** State transitions are triggered by commands (from wireless) or internal conditions (self-test results, safety violations). Each transition must be atomic and validated. If a state transition can be triggered while the device is in an inconsistent state (e.g., transitioning to CLOSED_LOOP while the DSP pipeline is still initializing), the controller may operate on uninitialized data. The firmware must enforce that transitions are only allowed from valid source states, and that the target state's prerequisites are met before the transition occurs.

## 11. OTA Firmware Update Security

### 11.1 OTA Update Architecture

Over-the-air firmware updates are the primary mechanism for deploying security patches, bug fixes, and feature updates to implanted devices. The OTA update mechanism is itself a critical security component — an insecure update mechanism is worse than no update mechanism, because it provides an attacker with a direct path to firmware installation.

```
External Programmer          IPG
      │                        │
      │  1. Session Init        │
      │ ──────────────────────> │
      │  2. Challenge/Response  │
      │ <────────────────────── │
      │  3. Update Request      │
      │ ──────────────────────> │
      │  4. Firmware Metadata   │
      │    (version, size, hash)│
      │ ──────────────────────> │
      │  5. Firmware Chunks     │
      │    (N x 256 bytes)      │
      │ ──────────────────────> │
      │  6. ACK per chunk       │
      │ <────────────────────── │
      │  ... repeat 5-6 ...     │
      │  7. Final Hash Verify   │
      │ ──────────────────────> │
      │  8. Signature Verify    │
      │     (bootloader)        │
      │  9. Commit / Reboot     │
      │ ──────────────────────> │
      │ 10. New firmware boots  │
      │ <────────────────────── │
```

### 11.2 Update Process Vulnerabilities

**Chunk-based transmission:** Firmware is transmitted in chunks (typically 256-1024 bytes) to handle the limited packet size and the need for acknowledgment. Each chunk is individually acknowledged. An attacker who can modify a chunk in transit (by compromising the wireless link) can inject malicious code into the firmware image. Mitigation: each chunk must be authenticated (HMAC or AEAD), and the complete image must be verified after all chunks are received.

**Interruption during update:** If the update is interrupted (e.g., the patient moves out of range, battery dies during update), the device must be left in a bootable state. A/B partitioning (Section 6.3) ensures that the old firmware remains intact until the new firmware is fully received and verified. Without A/B partitioning, an interrupted update can leave the device with a corrupted firmware image — bricking it until surgical replacement.

**Rollback attack:** If the update mechanism allows installation of an older firmware version, an attacker can force the device to run a firmware version with known vulnerabilities. Mitigation: monotonic version counter (Section 6.3). The challenge is that sometimes a legitimate rollback IS needed (e.g., a new firmware has a critical bug and must be reverted). The version counter must support authorized rollback while preventing unauthorized rollback.

**Supply chain attack:** If the firmware signing key is compromised (e.g., through an attack on the manufacturer's build infrastructure), an attacker can sign malicious firmware that the bootloader will accept. This is the most catastrophic attack on the OTA mechanism because it bypasses all cryptographic protections. Mitigation: hardware security modules (HSMs) for key storage, multi-party signing ceremonies, code review of all firmware changes.

### 11.3 Update Verification Pipeline

The bootloader's firmware verification pipeline before committing an update:

1. **Size check:** Verify the firmware image size matches the metadata. Prevents buffer overflows during verification.
2. **Hash verification:** Compute SHA-256 of the firmware binary and compare to the metadata. Detects corruption during transmission.
3. **Signature verification:** Verify the ECDSA/RSA signature over the hash using the stored public key. Authenticates the firmware source.
4. **Version check:** Verify the firmware version is greater than or equal to the current version (or equal to the current version if rollback is explicitly authorized).
5. **Hardware compatibility check:** Verify the firmware's target hardware revision matches the device's hardware revision. Prevents installing firmware for a different device variant.
6. **Image integrity verification (deep):** Optionally, verify the internal structure of the firmware image (valid vector table, sane section sizes, no overlapping regions).

**Security implication:** Each verification step is code that can itself contain vulnerabilities. A bug in the signature verification code (e.g., accepting any signature, skipping verification for certain image types, or a buffer overflow in the parsing code) compromises the entire update mechanism. The verification code should be as simple as possible and formally verified if feasible.

## 12. Power Management Firmware

### 12.1 Battery Constraints

Neurostimulator batteries are typically lithium-ion or lithium-carbon monofluoride (Li/CFx) cells with capacities of 100-500 mAh. The firmware must manage this energy budget carefully because:

- **Battery life is a clinical requirement:** Patients expect 3-15 years of battery life. Premature battery depletion requires surgical replacement.
- **Power consumption is attack-detectable:** Unusual power consumption patterns (e.g., continuous RF transmission due to a firmware bug) can indicate a security incident.
- **Low-power modes affect security:** Deep sleep modes disable the RF receiver, preventing the device from receiving security commands. An attacker who forces the device into deep sleep can create a DoS condition.

### 12.2 Power States

```
┌──────────┐  Therapy ON  ┌──────────┐  Wireless   ┌──────────┐
│  SLEEP   │ ──────────> │  ACTIVE  │ ─────────> │  TX/RX   │
│  (1 uW)  │             │ (5-20 mW) │             │ (50-100  │
│          │ <────────── │          │ <─────────  │   mW)    │
│  RF off  │  Therapy    │  RF wake  │  Session    │          │
│  Stim off│  complete   │  on demand│  end        │          │
└──────────┘             └──────────┘             └──────────┘
```

**Security implications:**
- **Sleep mode as attack surface:** When the device is in sleep mode, the RF receiver is typically off. An attacker cannot communicate with the device. However, if the device is forced into sleep mode during an active therapy session (by exploiting the power management firmware), therapy is interrupted — a DoS attack with direct clinical impact.
- **Battery drain attack:** An attacker who can increase the device's power consumption (e.g., by causing continuous RF transmission, increasing stimulation frequency, or disabling low-power modes) can drain the battery prematurely. This forces surgical replacement, causing patient harm and cost. Battery drain attacks have been demonstrated against pacemakers and are equally applicable to neurostimulators.
- **Voltage monitoring bypass:** The firmware monitors the battery voltage and enters a safe state when voltage drops below a threshold. If this monitoring is disabled (through firmware modification), the device may continue operating on a depleted battery, potentially delivering inconsistent stimulation or corrupting flash memory during a write operation.

## 13. Safety Monitor Firmware

### 13.1 Safety Monitor Requirements

The safety monitor is the firmware component that provides independent verification that the device is operating within safe parameters. It is the last line of defense between the firmware and patient harm.

**Functional safety requirements (IEC 61508 / ISO 26262 adapted for medical devices):**

1. **Independence:** The safety monitor must be independent of the main processing firmware. It should have its own code, its own data path, and ideally its own hardware (or at least a separate execution context that cannot be corrupted by the main firmware).

2. **Diversity:** The safety monitor should use different algorithms, different data representations, and different hardware resources than the main firmware. If the main firmware has a bug that causes incorrect stimulation, the safety monitor should detect it through an independent check.

3. **Fail-safe:** If the safety monitor detects a violation, it must halt stimulation in a safe manner (e.g., DC-blocking capacitor discharge, output relay open).

4. **Tamper-evident:** The safety monitor should be designed so that tampering is detectable. If the safety monitor's code or data is modified, it should either fail-safe or report the modification.

### 13.2 Safety Monitor Architecture

```
Main Processing Firmware           Safety Monitor
┌─────────────────────┐          ┌─────────────────────┐
│ Stimulation Params  │  shadow  │ Parameter Checker    │
│ (amplitude, PW,     │ ───────> │ Compares against     │
│  frequency, config) │          │ absolute limits       │
└─────────────────────┘          └──────────┬──────────┘
                                              │
                                              v
┌─────────────────────┐          ┌─────────────────────┐
│ Stimulation Driver  │  actual  │ Output Monitor       │
│ (register writes)   │ ───────> │ Reads back stim      │
│                     │          │ registers, compares   │
└─────────────────────┘          └──────────┬──────────┘
                                              │
                                              v
┌─────────────────────┐          ┌─────────────────────┐
│ DSP Engine          │  signal  │ Signal Plausibility  │
│ (band power, etc.)  │ ───────> │ Checks SNR, clipping,│
│                     │          │ feature ranges        │
└─────────────────────┘          └──────────┬──────────┘
                                              │
                                              v
                                   ┌─────────────────────┐
                                   │  Safety Action      │
                                   │  - Halt stimulation │
                                   │  - Log event        │
                                   │  - Alert (if able)  │
                                   └─────────────────────┘
```

### 13.3 Safety Monitor Independence Mechanisms

Achieving true independence in a single-MCU device is architecturally challenging:

| Mechanism | Independence Level | Feasibility | Security Strength |
|---|---|---|---|
| Separate task (RTOS) | Software separation | Easy | Weak — shared memory, shared MPU domain |
| MPU-isolated region | Hardware isolation | Easy-medium | Medium — cannot read/write monitor's memory from main code |
| Separate core (dual-core MCU) | Hardware isolation | Medium | Strong — independent execution, but shared bus |
| Separate chip (safety ASIC) | Full isolation | Hard | Strongest — independent power, execution, and I/O |

Most current neurostimulators use the RTOS task approach (software separation) because it is the simplest and cheapest. Some newer devices use MPU isolation. Very few use separate safety ASICs due to the cost and complexity of integrating a second chip.

**Security analysis:** Software-only safety monitors are vulnerable to the same memory corruption attacks as the main firmware. If an attacker exploits a buffer overflow in the wireless stack, they can potentially corrupt the safety monitor's task memory (if they can predict its address) or disable the safety monitor task (by corrupting the RTOS task control block). MPU isolation significantly raises the bar but is still bypassable through MPU misconfiguration or JTAG/SWD debug access.

### 13.4 Safety Monitor Bypass Techniques

An attacker who compromises the main firmware can attempt to bypass the safety monitor through several techniques:

1. **Direct memory write:** If the safety monitor's parameter limits are stored in RAM that the main firmware can access, the attacker can modify the limits to be very large, effectively disabling the safety check.

2. **Task suspension:** If the RTOS allows one task to suspend another, the attacker (running in the main firmware context) can suspend the safety monitor task.

3. **Watchdog starvation:** The safety monitor may use a hardware watchdog timer. If the attacker can prevent the watchdog from being serviced (by corrupting the kick routine or by disabling the timer), the watchdog will reset the device — which may be the attacker's goal (DoS through forced reboot).

4. **Shadow register poisoning:** The safety monitor reads a "shadow" copy of the stimulation parameters. If the attacker can make the shadow copy match the malicious parameters (by corrupting the shadow update mechanism), the safety monitor will see consistent (but unsafe) values.

VIREON should validate that the safety monitor cannot be bypassed by any of these techniques.

## 14. Diagnostic and Telemetry Firmware

### 14.1 Diagnostic Data Pipeline

The diagnostic firmware collects operational data from the device for clinical and engineering purposes:

```
Internal Data Sources              Diagnostic Logger              External Telemetry
┌──────────────────┐            ┌──────────────────┐            ┌──────────────────┐
│ Stimulation      │            │ Circular buffer   │            │ Wireless TX       │
│ parameters       │ ──────────> │ (4-16 KB SRAM)    │ ──────────> │ (encrypted,       │
│ Signal quality   │            │ FIFO overwrite    │            │  authenticated)   │
│ Battery status   │            │                   │            │                  │
│ Impedance values │            │ Flash storage     │            │ Programmer/Cloud  │
│ Error/Event logs │            │ (when available)  │            │                  │
│ Safety events    │            │                   │            │                  │
└──────────────────┘            └──────────────────┘            └──────────────────┘
```

### 14.2 Data Exfiltration Risks

The diagnostic pipeline is a potential data exfiltration channel. An attacker who compromises the firmware can use the diagnostic telemetry to exfiltrate sensitive data:

- **Neural signals:** Raw or processed neural data reveals the patient's neural state, which can reveal medical conditions, cognitive states, or even intended actions (in BCI systems).
- **Stimulation parameters:** Current therapy settings reveal the patient's diagnosis and treatment plan.
- **Calibration data:** Device-specific calibration data can be used to craft targeted attacks on the specific device.
- **Encryption keys:** If the firmware stores session keys or pairing secrets in a format that the diagnostic logger can access, these can be exfiltrated.

**Security implication:** The diagnostic logger should be the LEAST privileged subsystem in the firmware. It should not have access to encryption keys, pairing secrets, or raw neural data. The data it collects should be aggregated and anonymized to the maximum extent possible. VIREON should verify that the diagnostic data pipeline does not provide a path to sensitive data.

### 14.3 Telemetry Bandwidth Constraints

The MICS band (402-405 MHz) provides approximately 250-800 kbps data rate. This bandwidth must support:
- Incoming commands (low bandwidth: ~1-10 kbps)
- Outgoing telemetry (variable: 10-250 kbps)
- Acknowledgments and protocol overhead

**Security implication:** The limited bandwidth constrains the security measures that can be applied to telemetry. Full TLS 1.3 with certificate verification requires multiple round trips and significant overhead. Most neurostimulator telemetry uses lightweight AEAD (AES-CCM or AES-GCM) with pre-shared keys, which adds only 16 bytes of overhead per packet. The trade-off is that pre-shared keys provide weaker security properties than certificate-based authentication.

## 15. Firmware Attack Surface Map

### 15.1 Comprehensive Attack Surface

| Attack Vector | Entry Point | Exploitation Method | Impact | Detectability |
|---|---|---|---|---|
| Wireless command injection | RF receiver → command parser | Malformed packet exploits parser vulnerability | Code execution, parameter modification | Medium — protocol analysis |
| Firmware update hijacking | RF receiver → bootloader | Supply chain attack or downgrade | Persistent firmware compromise | Low — appears legitimate |
| Buffer overflow (signal) | AFE → DMA → signal buffer | Large signal exceeds buffer size | Memory corruption, code execution | High — unusual signal patterns |
| Buffer overflow (wireless) | RF → DMA → rx buffer | Large packet exceeds rx buffer size | Memory corruption, code execution | Medium — packet monitoring |
| Integer overflow | Any arithmetic on untrusted input | Out-of-bounds access via overflowed index | Memory corruption | Low — no visible symptoms |
| Return-oriented programming (ROP) | Any code execution primitive | Chain gadgets in existing code | Arbitrary code execution | Low — uses legitimate code |
| DMA attack | DMA controller | DMA writes to arbitrary addresses | Memory corruption | Low — bypasses CPU |
| Fault injection | External (EMI, laser, voltage glitch) | Causes bit flips in SRAM/flash | Logic change, key extraction | Variable — requires physical proximity |
| Side-channel (timing) | Any secret-dependent operation | Measures execution time to infer secrets | Key extraction | Low — passive, no modification |
| Side-channel (power) | Any secret-dependent operation | Measures power consumption | Key extraction | Low — requires physical proximity |
| MPU misconfiguration | Boot sequence | Writes to MPU registers | Privilege escalation | Low — no visible symptom |
| Safety monitor bypass | Any memory write | Corrupts monitor state or task | Disable safety checks | Low — safety checks stop silently |

### 15.2 Attack Surface Ordering (VIREON Priority)

VIREON should prioritize validation of the attack surface based on exploitability and impact:

1. **Critical:** Wireless command parser (highest exposure, highest impact)
2. **Critical:** OTA update mechanism (persistent compromise)
3. **High:** Stimulation parameter validation (direct patient safety)
4. **High:** Safety monitor independence (last line of defense)
5. **Medium:** DSP engine buffer management (memory corruption)
6. **Medium:** RTOS task isolation (privilege escalation)
7. **Low:** Diagnostic data pipeline (data exfiltration, lower immediate impact)

## 16. Known Firmware Vulnerabilities

### 16.1 Abbott (St. Jude) Medical Devices (2016-2017)

**Vulnerability:** The Merlin@home transmitter communicated with implantable devices using unencrypted radio frequency. Firmware updates were transmitted without adequate authentication.

**Impact:** An attacker within range (approximately 10 meters for the home transmitter, longer with specialized equipment) could:
- Modify device settings without authorization
- Drain the battery by causing rapid stimulation cycling
- Potentially deliver unsafe stimulation

**Root cause:** The firmware's communication stack did not implement encryption or authentication for the home monitoring communication channel. The clinical programmer channel was encrypted, but the home monitoring channel was not (presumably for power/bandwidth reasons).

**Remediation:** FDA advisory, firmware update adding encryption to the home monitoring channel.

**VIREON lesson:** Every communication channel must be secured, not just the "primary" channel. Attackers will find and exploit the weakest link. VIREON's validation framework should test ALL communication channels, not just the clinical programmer interface.

### 16.2 Medtronic Insulin Pump (2011-2019, Multiple)

**Vulnerability:** Multiple vulnerabilities in Medtronic's MiniMed insulin pumps, some related to firmware. While not a neurostimulator, the firmware architecture and attack patterns are directly applicable.

**Key firmware-related issue:** The pump's firmware accepted commands from any paired device without verifying the command's authorization level. A paired device with limited authorization (e.g., a blood glucose monitor) could send commands that required higher authorization (e.g., change basal rate).

**VIREON lesson:** The command parser must enforce per-command authorization, not just per-session authorization. Each command should be checked against the sender's authorization level. VIREON should verify that the firmware implements per-command authorization correctly.

### 16.3 Generic Cortex-M Exploitation Techniques

While no published neurostimulator firmware exploits exist in the public literature (as of 2025), the following Cortex-M exploitation techniques are well-documented and directly applicable:

**Stack buffer overflow:** The classic attack. An unchecked copy into a stack-allocated buffer overwrites the return address, redirecting code execution. On Cortex-M, the return address is on the stack (no canary by default, though compilers can add them). The return address is popped into PC on function return (`BX LR` or `POP {PC}`).

**Heap overflow:** If dynamic allocation is used, overflowing a heap buffer corrupts the allocator's metadata (free list pointers). By corrupting a free list pointer, an attacker can cause a subsequent allocation to return a pointer to an arbitrary address ("unlink" attack, applicable to simple allocators without integrity checks).

**Return-oriented programming (ROP):** Even without injecting new code, an attacker can chain existing code fragments ("gadgets" ending in `BX LR`) to achieve arbitrary computation. On Cortex-M, ROP is straightforward because there is no ASLR (addresses are fixed at link time), no DEP (flash is typically both writable and executable, and the MPU's XN bit is often not configured for code regions), and no stack canaries (unless explicitly enabled by the compiler).

**Format string attack:** If the firmware uses `printf` or `sprintf` with user-controlled format strings, an attacker can read arbitrary memory (`%x`, `%s`) or write arbitrary memory (`%n`). Format string vulnerabilities are common in diagnostic logging code that formats error messages containing user input.

## 17. Firmware Reverse Engineering Methodology

### 17.1 Static Analysis

Static analysis examines the firmware binary without executing it:

1. **File identification:** Use `file`, `binwalk`, `binwalk -E` to identify the firmware image format, compression, and embedded components.

2. **String extraction:** `strings -n 6 firmware.bin` extracts readable strings — function names, error messages, debug strings, version strings. These provide immediate insight into the firmware's functionality and can reveal security-relevant strings (key material, URLs, debug interfaces).

3. **Disassembly:** Use Ghidra, IDA Pro, or Binary Ninja to disassemble the ARM binary. The disassembler identifies functions, basic blocks, and cross-references.

4. **Function identification:** Look for known function patterns:
   - AES: 256-byte S-box lookup table at offset 0x...
   - SHA-256: 64-byte round constants (K)
   - CRC: Lookup table with 256 entries of polynomial evaluations
   - Signal processing: Arrays of filter coefficients (recognizable spectral shapes)

5. **Control flow reconstruction:** Identify the RTOS task structure by looking for the RTOS's task creation API calls (e.g., `xTaskCreate` for FreeRTOS). This reveals the task architecture described in Section 4.2.

6. **Security function audit:** Identify and audit all functions that handle: wireless input, parameter validation, cryptographic operations, memory allocation, and safety checks.

### 17.2 Dynamic Analysis

Dynamic analysis examines the firmware's behavior during execution:

1. **Emulation:** Run the firmware binary in an emulator (QEMU for ARM, or VIREON's digital twin). This allows single-stepping, breakpoint setting, and memory inspection without physical hardware.

2. **Fault injection simulation:** Simulate fault injection by modifying registers or memory at specific points during execution. For example, flip a bit in the stimulation amplitude register and observe whether the safety monitor detects the modification.

3. **Fuzzing:** Provide random or semi-random inputs to the wireless command parser and observe whether the firmware crashes, hangs, or behaves unexpectedly. Fuzzing is the most effective technique for finding parser vulnerabilities.

4. **Timing analysis:** Measure the execution time of security-critical operations (signature verification, decryption) to detect timing side-channels.

### 17.3 VIREON Firmware Analysis Integration

VIREON's firmware analysis capabilities should provide:

- **Automated function identification:** Pattern matching for known cryptographic and DSP functions.
- **Control flow graph extraction:** Automated extraction of the firmware's function call graph and basic block structure.
- **Security annotation overlay:** Map the firmware's functions to the security-critical operations described in this module.
- **Compliance checking:** Verify that the firmware implements the security measures described in IEC 62304 Annex C (security recommendations).

## 18. Firmware Hardening Techniques

### 18.1 Compile-Time Hardening

| Technique | Description | Applicability to IPG | Overhead |
|---|---|---|---|
| Stack canaries | Compiler-inserted integrity check before function return | High — detects stack overflows | 1-2% code size, minimal CPU |
| NX/DEP (XN bit) | MPU execute-never regions prevent code execution from data areas | High — prevents shellcode injection | None (hardware feature) |
| ASLR | Randomize code/data addresses at each boot | Limited — no MMU on Cortex-M, only MPU with fixed regions | None |
| RELRO | Read-only relocations, prevent GOT/PLT overwrite | Medium — prevents some ROP gadgets | Minimal |
| FORTIFY_SOURCE | Replace unsafe C functions with bounds-checked versions | High — prevents many buffer overflows | 1-3% code size |
| Control flow integrity (CFI) | Verify that indirect branches target valid call sites | Medium — prevents ROP | 5-15% code size, 5-10% CPU |
| Bounds checking | Compiler-inserted array bounds checks | High — prevents out-of-bounds access | 10-30% code size, 10-20% CPU |

**Security analysis for IPG constraints:** The CPU overhead of bounds checking (10-20%) may be unacceptable for time-critical code paths (stimulation timing, DSP processing). The recommended approach is to use hardening selectively: full hardening for non-real-time code (wireless stack, diagnostic logger) and selective hardening for real-time code (DSP, stimulation timing). The safety monitor should have the highest level of hardening since it is the last line of defense.

### 18.2 Runtime Hardening

| Technique | Description | Applicability |
|---|---|---|
| Watchdog timer | Hardware timer that resets the MCU if not serviced periodically | Essential — detects firmware hangs |
| Memory fill patterns | Fill freed memory with a known pattern (0xDEAD...) to detect use-after-free | Useful for debugging, minimal runtime cost |
| Stack fill patterns | Fill stack with a pattern to detect stack overflow after task switch | Essential — detects stack overflows |
| Double-buffering | Use two buffers for shared data, atomically swap | Essential — prevents torn reads/writes |
| Input validation | Validate ALL external inputs (wireless commands, ADC values) | Essential — first line of defense |
| Fail-safe defaults | If validation fails, use the safest default value | Essential — safety-critical systems |
| Redundant computation | Compute critical values twice using different methods and compare | High overhead, use only for safety-critical computations |

### 18.3 Architecture-Level Hardening

| Technique | Description | Applicability |
|---|---|---|
| MPU region isolation | Separate firmware subsystems into isolated MPU regions | Essential — hardware-enforced isolation |
| TrustZone (M33) | Separate secure/non-secure worlds with hardware boundary | Strongest software-level isolation on Cortex-M |
| Separate safety core | Use a dual-core MCU with the safety monitor on a separate core | Strongest isolation, highest cost |
| Secure boot | Verify firmware integrity before execution | Essential — prevents firmware tampering |
| Secure debug | Disable JTAG/SWD after manufacturing, or require authentication | Essential — prevents physical debug access |
| Flash protection | Set flash read/write protection bits after programming | Essential — prevents firmware extraction/modification |
| Bus encryption | Encrypt data on the internal bus between MCU and peripherals | Emerging — prevents bus probing |

**VIREON validation:** For each hardening technique, VIREON should verify that it is correctly implemented and that it cannot be bypassed. This requires analyzing the firmware's initialization code (to verify MPU configuration), the linker script (to verify memory layout), and the RTOS configuration (to verify task isolation).