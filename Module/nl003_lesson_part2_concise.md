# NL-003: Neurostimulator Firmware Architecture (Part 2)

## 9. DSP Firmware: The Signal Processing Engine

### 9.1 Fixed-Point vs. Floating-Point

Neural signal processing in the IPG runs on the MCU. The numerical representation choice (fixed-point vs. floating-point) has security implications:

**Fixed-point (int16_t, int32_t):** Deterministic, fast, no FPU required. But prone to overflow, truncation, and precision loss. An attacker who understands the fixed-point scaling can craft inputs that cause specific overflow patterns.

**Floating-point (float32_t):** Wider dynamic range, easier to program. Requires FPU (Cortex-M4F). Non-deterministic across different FPU implementations (potential reproducibility issue for VIREON).

**Security implication:** If the firmware uses fixed-point for band power computation, the accumulated rounding error depends on the signal characteristics. An attacker who injects a signal that maximizes rounding error can cause the band power estimate to be systematically biased. This bias could shift the closed-loop controller's operating point.

### 9.2 Filter Implementation in Firmware

The filters described in NL-002 are implemented in firmware as either IIR or FIR. Each implementation has firmware-specific vulnerabilities:

**FIR filter (circular buffer):**
```c
// Simplified FIR filter implementation
int32_t fir_filter(int32_t *coeffs, int n_coeffs, int32_t *buffer, int *index) {
    int32_t acc = 0;
    int idx = *index;
    for (int i = 0; i < n_coeffs; i++) {
        acc += (int64_t)coeffs[i] * buffer[idx] >> 15; // Q15 multiply
        idx = (idx - 1 + BUFFER_SIZE) % BUFFER_SIZE;
    }
    *index = (*index + 1) % BUFFER_SIZE;
    return acc;
}
```
Vulnerabilities: The circular buffer index calculation can wrap incorrectly if `BUFFER_SIZE` is not a power of 2 and the modulo operation is optimized away. The `>> 15` right shift truncates (rounds toward negative infinity), not rounds toward zero — this asymmetry can be exploited.

**IIR filter (Direct Form II):**
```c
// Simplified IIR filter (Direct Form II Transposed)
void iir_filter(float *b, float *a, int order,
               float *x, float *y, int n_samples,
               float *state) {
    for (int i = 0; i < n_samples; i++) {
        float acc = b[0] * x[i] + state[0];
        for (int j = 1; j <= order; j++) {
            state[j-1] = x[i] * b[j] - y[i] * a[j] + state[j];
        }
        y[i] = acc;
    }
}
```
Vulnerabilities: The state array contains the filter's internal state. If an attacker can overwrite the state (via buffer overflow or memory corruption), they can force the filter to produce arbitrary output. The `a` coefficients (feedback) can cause instability if modified.

### 9.3 DMA for Signal Acquisition

Direct Memory Access (DMA) transfers ADC samples directly to SRAM without CPU intervention. In an IPG, DMA is typically configured for:
- ADC → SRAM: Neural signal acquisition
- SRAM → RF module: Telemetry data transmission

**Security implication:** DMA operates independently of the CPU. The DMA configuration (source address, destination address, transfer count, channel enable) is set by the firmware. If an attacker can modify DMA configuration registers (via firmware vulnerability or peripheral register access), they can:
- Redirect ADC data to arbitrary SRAM locations (potentially overwriting firmware code)
- Transmit arbitrary SRAM contents over the RF link (information disclosure)

VIREON must verify that DMA configuration is locked after initialization.

## 10. Telemetry Protocol Firmware

### 10.1 Protocol Handler Architecture

The telemetry handler is the primary attack surface in IPG firmware. It processes incoming wireless data and generates outgoing responses. A typical architecture:

```c
void telemetry_interrupt_handler(void) {
    uint8_t byte = rf_module_read_byte();
    
    switch (telemetry_state) {
        case WAITING_FOR_PREAMBLE:
            if (byte == PREAMBLE_BYTE) {
                telemetry_state = RECEIVING_HEADER;
                header_buffer[0] = byte;
                header_index = 1;
            }
            break;
            
        case RECEIVING_HEADER:
            header_buffer[header_index++] = byte;
            if (header_index >= HEADER_LENGTH) {
                parse_header(&current_header, header_buffer);
                if (current_header.length > MAX_PAYLOAD) {
                    telemetry_state = WAITING_FOR_PREAMBLE; // Reject
                    break;
                }
                telemetry_state = RECEIVING_PAYLOAD;
                payload_index = 0;
            }
            break;
            
        case RECEIVING_PAYLOAD:
            payload_buffer[payload_index++] = byte;
            if (payload_index >= current_header.length) {
                process_command(&current_header, payload_buffer);
                telemetry_state = WAITING_FOR_PREAMBLE;
            }
            break;
    }
}
```

**Vulnerability analysis:**

1. **Buffer overflow in payload_buffer:** If `current_header.length` is not validated against `MAX_PAYLOAD` (it is in this example, but may not be in all implementations), a malicious header with a large length value causes the payload to overflow the buffer. This is the #1 vulnerability class in embedded firmware.

2. **State machine escape:** The `parse_header` function may not validate all header fields. An unexpected header value could put the state machine into an undefined state, potentially bypassing authentication or enabling unauthorized operations.

3. **Timing side-channel:** The time taken to process different commands may differ. An attacker who measures the response latency can infer which code path was taken, leaking information about internal state (e.g., whether authentication succeeded or failed).

### 10.2 Command Processing

After a complete frame is received, the payload is processed:

```c
void process_command(Header *hdr, uint8_t *payload) {
    if (!authenticated) {
        if (hdr->type == CMD_AUTH_CHALLENGE) {
            handle_authentication(payload);
            return;
        }
        reject_command(CMD_REJECT_NOT_AUTHENTICATED);
        return;
    }
    
    switch (hdr->type) {
        case CMD_READ_PARAMS:
            send_stimulation_params();
            break;
        case CMD_WRITE_PARAMS:
            // VULNERABILITY: Is parameter validation sufficient?
            update_stimulation_params(payload);
            break;
        case CMD_READ_LFP:
            send_lfp_data();
            break;
        case CMD_FIRMWARE_UPDATE:
            handle_firmware_update(payload);
            break;
        default:
            reject_command(CMD_REJECT_UNKNOWN);
    }
}
```

The `update_stimulation_params` function is the highest-impact function in the firmware. A vulnerability here enables direct manipulation of stimulation. VIREON's firmware analysis must identify this function and verify that its parameter validation is complete.

## 11. Stimulation Controller Firmware

### 11.1 Pulse Generation

The stimulation controller generates precisely timed electrical pulses. Implementation typically uses a hardware timer with DMA:

1. Configure the timer for the desired pulse width (60-450 us)
2. Configure the inter-pulse interval (1/frequency - pulse_width)
3. Enable the timer interrupt or DMA to toggle the DAC output
4. The DAC drives the constant-current stimulation circuitry

**Security-critical timing requirements:**
- Pulse width accuracy: +/- 5 us (a 10 us error at 450 us pulse width is 2.2%)
- Frequency accuracy: +/- 1 Hz
- Phase accuracy (for phase-locked stimulation): +/- 5 degrees

### 11.2 Stimulation State Machine

``n
    +--------+  power-on  +--------+  start    +--------+  pause   +--------+
    | IDLE   |----------->| INIT   |---------->| ACTIVE  |--------->| PAUSED  |
    +--------+           +--------+          +--------+         +--------+
         ^                                          |                |
         |                                          v                |
         +--------------------------------------+  resume         |
                                                  +--------+
```

The state machine must be robust against unexpected state transitions. An attacker who can cause a transition from IDLE directly to ACTIVE (bypassing INIT) could deliver stimulation with uninitialized parameters. VIREON must verify that the state machine enforces the correct transition sequence.

## 12. Safety Monitor Firmware Interface

### 12.1 Hardware vs. Firmware Safety Monitor

The safety monitor exists at two levels:

**Hardware safety monitor (always active):** An independent circuit that compares the actual stimulation output (voltage, current, charge per phase) against hard-coded limits. Cannot be disabled or bypassed by firmware. This is the last line of defense.

**Firmware safety monitor (software, verified):** A software module that performs additional checks beyond the hardware monitor's capabilities:
- Verifies that commanded parameters are within the therapist-programmed range (narrower than the hardware limits)
- Monitors for rapid parameter changes that could indicate an attack
- Implements therapy duration limits
- Logs parameter changes for audit

**Security gap:** The firmware safety monitor can be bypassed by firmware attacks. The hardware safety monitor cannot be bypassed but has limited capability (it checks instantaneous values, not trends or intent). An attacker who compromises the firmware but respects the hardware limits can set any stimulation parameter within those limits.

### 12.2 Safety Monitor Configuration

The hardware safety monitor's limits are typically configured at implantation through one-time-programmable fuses:

``n
Hardware Safety Limits (non-modifiable):
  Max voltage:       10.5 V  (for 10.0 V therapeutic max + 0.5 V margin)
  Max current:       15.0 mA (for 14.0 mA therapeutic max + 1.0 mA margin)
  Max charge/phase:  4.0 uC  (for 3.5 uC therapeutic max + 0.5 uC margin)
  Max frequency:     250 Hz  (for 185 Hz therapeutic max + 65 Hz margin)
  Max duty cycle:    50%    (conservative)

Firmware Safety Limits (configured by clinician):
  Max voltage:       configured per patient (e.g., 3.5 V)
  Max current:       configured per patient (e.g., 5.0 mA)
  Max frequency:     configured per patient (e.g., 185 Hz)
  Max pulse width:    configured per patient (e.g., 210 us)
```

VIREON must verify that the firmware safety limits are correctly enforced and that the hardware safety limits are properly configured.

## 13. Firmware Update Mechanisms

### 13.1 Update Delivery

Firmware updates are delivered wirelessly during a programming session. The process:

1. Clinician initiates firmware update from the programmer
2. Programmer sends the new firmware image in chunks (limited by MICS bandwidth)
3. IPG writes each chunk to a backup flash region
4. After all chunks are received, IPG verifies the new firmware's signature
5. If verification passes, IPG swaps the active firmware pointer to the new region
6. IPG resets and boots the new firmware

### 13.2 Security Requirements for Firmware Updates

1. **Authenticated update initiation:** Only authenticated programmers can initiate updates. The update command must be cryptographically authenticated.

2. **Atomic update:** The new firmware is written to a backup region. The active firmware continues running until the update is complete and verified. If the update fails (power loss, verification failure), the device continues running the old firmware.

3. **Signed firmware image:** The new firmware image must be signed by the manufacturer. The bootloader verifies the signature before activating the new firmware.

4. **Version enforcement:** The new firmware version must be >= the current version (anti-rollback protection). This prevents installation of older, vulnerable firmware.

5. **Rollback capability:** If the new firmware causes a problem (detected within the first programming session after update), the device should be able to revert to the previous firmware. This requires keeping the old firmware in a third flash region.

### 13.3 Firmware Update Vulnerabilities

**Update chunk reordering:** If individual chunks are not authenticated (only the final image is authenticated), an attacker could reorder chunks to corrupt specific functions. Defense: authenticate each chunk individually, or verify chunk ordering.

**Partial update:** If the device boots the new firmware before the update is complete (e.g., due to a premature reset), the partially updated firmware will be non-functional. Defense: the active firmware pointer is only updated after the complete image is verified.

**Supply chain attack on the update package:** If the firmware update package is intercepted in transit (between manufacturer and programmer, or between programmer and implant), the attacker can replace it with a malicious image. Defense: end-to-end encryption and authentication from manufacturer to implant.

## 14. Firmware Reverse Engineering Methodology

### 14.1 Firmware Acquisition

Before analyzing firmware, you must obtain it. Methods (in order of difficulty):

1. **Regulatory submission:** FDA pre-market submissions (510(k), PMA) may include firmware binaries or firmware specifications. Some of this information is publicly accessible through the FDA 510(k) database.

2. **Update package interception:** If firmware updates are transmitted over-the-air, the update package can be captured using a compatible SDR.

3. **Hardware extraction:** Removing the chip from the device and reading the flash using a debugger or specialized flash reader. Destructive — requires access to an explanted or spare device.

4. **JTAG/SWD access:** If the debug interface is not properly disabled, firmware can be read directly through the debug port. Non-destructive but requires physical access to the device.

### 14.2 Static Analysis Methodology

VIREON's firmware analysis follows this sequence:

1. **File format identification:** Determine the firmware file format (raw binary, Intel HEX, ELF, vendor-specific). Tool: `file`, `binwalk`.

2. **Header extraction:** Extract firmware metadata (version, build date, device type, checksums). Tool: `binwalk -E`, custom header parser.

3. **String extraction:** Extract all printable strings (error messages, debug strings, protocol keywords, configuration data). Tool: `strings`, custom string extractor.

4. **Memory mapping:** Map the firmware to the processor's memory space (identify code, data, BSS, and unused regions). Tool: custom mapper, ELF parser if applicable.

5. **Function identification:** Identify key functions by pattern matching (known function prologues/epilogues, string references, call patterns). Tool: Ghidra, IDA Pro, custom pattern matcher.

6. **Security-critical function analysis:** Detailed analysis of the telemetry handler, parameter validation, and safety monitor configuration. Tool: manual review with Ghidra/IDA.

7. **Cryptographic analysis:** Identify cryptographic implementations, key storage, and protocol usage. Tool: `findcrypt`, manual review.

### 14.3 Dynamic Analysis (When Hardware Available)

When a physical device is available for testing:

1. **Fuzzing:** Send malformed packets to the wireless interface and observe the device's response. Tool: custom fuzzer using HackRF/USRP.

2. **Side-channel analysis:** Measure power consumption or electromagnetic emissions during cryptographic operations to extract keys. Tool: ChipWhisperer, custom EM probes.

3. **Fault injection:** Apply voltage glitching or clock glitching during firmware execution to skip security checks. Tool: ChipWhisperer glitch module.

Dynamic analysis is outside the scope of this module's labs (requires hardware) but is described for completeness and as a VIREON future capability.