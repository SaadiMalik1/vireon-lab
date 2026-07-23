# NL-003: Neurostimulator Firmware Architecture and Security (Part 1)

## 1. Why Firmware Is the Core Attack Surface

### 1.1 The Firmware Primacy Principle

In a neurostimulator, firmware is the layer that translates hardware capabilities into clinical behavior. The AFE ASIC can sample at 30 kS/s, but firmware decides what to sample, how to filter it, and what to do with the result. The RF transceiver can transmit at 800 kbps, but firmware decides what data to send and whether to encrypt it. The stimulation circuitry can deliver pulses from 0-10 mA, but firmware decides the pulse width, frequency, and amplitude — and whether to deliver them at all.

This primacy makes firmware the single most consequential attack surface in the entire neurostimulator ecosystem. A vulnerability in the wireless protocol (NL-004) is serious but limited to data in transit. A vulnerability in the closed-loop algorithm (NL-005) is serious but may be detectable through output monitoring. A firmware vulnerability, however, can compromise everything simultaneously: it can disable the safety monitor, modify the stimulation parameters, exfiltrate neural data, and persist across reboots — all from a single exploit.

### 1.2 The Immutability Problem

Unlike a server, a phone, or even a car's ECU, an implanted neurostimulator's firmware cannot be physically accessed after implantation. If a firmware vulnerability is discovered post-implant, the only remediation paths are:

- **Over-the-air (OTA) update:** Wirelessly push new firmware. This is the intended path but introduces its own attack surface (Section 11). The update channel itself must be secured, and a failed update can brick the device.
- **Surgical revision:** Remove and replace the device. This is the last resort — it exposes the patient to surgical risks, costs tens of thousands of dollars, and may not be feasible for all patients.
- **No remediation:** Accept the vulnerability and rely on external defenses (external programmer security, hospital network security). This is the reality for many currently implanted devices.

This immutability problem means that firmware security is not just a development concern — it is a lifecycle concern that extends for the entire device lifetime (typically 5-15 years). A firmware bug discovered in year 3 of a 10-year device lifetime affects all currently implanted patients.

### 1.3 Firmware as Trust Anchor

Firmware is also the trust anchor for the entire device. The secure boot chain (Section 6) verifies firmware integrity at startup. If the firmware itself is compromised, all downstream trust is broken: the safety monitor cannot be trusted to halt unsafe stimulation, the encryption keys cannot be trusted to protect wireless communication, and the diagnostic data cannot be trusted to reflect the device's true state.

This trust anchor property means that firmware is the highest-value target for an attacker. A single firmware-level compromise provides the deepest, most persistent access to the device — far beyond what protocol-level or application-level attacks can achieve.

### 1.4 Regulatory Context: IEC 62304

Medical device firmware development is governed by IEC 62304 (Medical device software — Software life cycle processes). This standard defines software safety classes (A, B, C) based on the potential for injury:

- **Class A:** No injury possible — not applicable to neurostimulators.
- **Class B:** Non-serious injury possible — applicable to diagnostic-only features.
- **Class C:** Death or serious injury possible — applicable to all stimulation and closed-loop features.

For Class C software, IEC 62304 requires: formal requirements traceability, unit testing with 100% statement and branch coverage for safety-critical code, code reviews, configuration management, risk management per ISO 14971, and maintained documentation throughout the device lifecycle. However, IEC 62304 is a process standard, not a security standard. It ensures that the development process was followed but does not guarantee that the resulting firmware is secure against deliberate attack. A firmware image can be fully IEC 62304 compliant and still contain buffer overflows, hardcoded keys, or insecure update mechanisms.

## 2. IPG Firmware Architecture Overview

### 2.1 Functional Subsystem Decomposition

IPG firmware is typically organized into the following subsystems, each with distinct security responsibilities:

```
┌─────────────────────────────────────────────────────┐
│                 APPLICATION LAYER                    │
│  ┌──────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │ Therapy   │ │ Closed-Loop  │ │ Diagnostic     │  │
│  │ Manager   │ │ Controller   │ │ Data Logger    │  │
│  └──────────┘ └──────────────┘ └────────────────┘  │
├─────────────────────────────────────────────────────┤
│                 SERVICE LAYER                        │
│  ┌──────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │ DSP      │ │ Stimulation  │ │ Safety         │  │
│  │ Engine   │ │ Pulse Gen    │ │ Monitor        │  │
│  └──────────┘ └──────────────┘ └────────────────┘  │
├─────────────────────────────────────────────────────┤
│                 HAL / DRIVER LAYER                   │
│  ┌──────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │ AFE      │ │ RF Telemetry │ │ Power Mgmt     │  │
│  │ Driver   │ │ Driver       │ │ Driver         │  │
│  └──────────┘ └──────────────┘ └────────────────┘  │
├─────────────────────────────────────────────────────┤
│                 RTOS / PLATFORM LAYER                │
│  ┌──────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │ Scheduler │ │ Memory Mgmt  │ │ Interrupt      │  │
│  │          │ │             │ │ Controller     │  │
│  └──────────┘ └──────────────┘ └────────────────┘  │
├─────────────────────────────────────────────────────┤
│                 HARDWARE ABSTRACTION                  │
│  ARM Cortex-M MCU + AFE ASIC + RF + Stim Circuit    │
└─────────────────────────────────────────────────────┘
```

Each layer introduces its own attack surface:

| Layer | Security Function | Attack Surface |
|---|---|---|
| Application | Clinical logic, parameter validation | Logic bugs, state machine errors, authorization bypass |
| Service | DSP, stimulation generation, safety monitoring | Algorithm manipulation, timing attacks, safety monitor bypass |
| HAL/Driver | Hardware access, DMA, interrupts | Buffer overflows, DMA attacks, race conditions |
| RTOS | Task scheduling, memory protection | Scheduler manipulation, MPU misconfiguration, priority inversion |

### 2.2 The Concurrency Model

Neurostimulator firmware must handle multiple concurrent real-time requirements:

1. **Stimulation timing:** Pulses must be delivered with microsecond precision. A 1 ms timing error in a 130 Hz DBS system could cause a phase error of 47 degrees — potentially reducing therapeutic efficacy or causing side effects.
2. **Signal acquisition:** Neural signals must be sampled at a consistent rate without dropped samples. A single dropped sample creates an impulse artifact in the frequency domain.
3. **Wireless communication:** Incoming commands must be processed within the protocol's timeout window (typically 100-500 ms for MICS).
4. **Safety monitoring:** Safety checks must run at a rate that can detect and halt unsafe stimulation before patient harm occurs. For stimulation, this means sub-millisecond response time.

These requirements are typically met using an RTOS with priority-based preemptive scheduling. The highest priority is assigned to the stimulation pulse generator and safety monitor, followed by signal acquisition, then wireless communication, and finally background tasks like data logging and diagnostic self-tests.

**Security implication:** The priority assignment itself is a security-critical decision. If the wireless communication handler has higher priority than the safety monitor, an attacker who floods the wireless interface can starve the safety monitor of CPU time — a priority inversion attack that prevents the device from detecting unsafe stimulation. Conversely, if the safety monitor has the highest priority but is implemented with a bug that causes it to hang (e.g., deadlock, infinite loop), it can block all lower-priority tasks including stimulation, causing therapy interruption.

### 2.3 Memory Budget

A typical IPG firmware memory budget demonstrates the extreme resource constraints:

| Resource | Typical Value | Primary Consumer |
|---|---|---|
| Flash (code) | 256 KB - 1 MB | DSP algorithms, protocol stack, clinical logic |
| SRAM (data) | 64 KB - 256 KB | Signal buffers, FFT buffers, state variables |
| Register file | 32 x 32-bit | Interrupt handling, real-time control |
| Backup RAM | 4-16 KB | Safety-critical state, stimulation parameters |

**Security implication:** These constraints directly limit the security measures that can be implemented. AES-256 encryption requires 320 bytes of lookup tables (or 1 KB for T-tables) — significant in a device with 64 KB SRAM. SHA-256 requires 64 bytes of state and 64 bytes of block buffer. A full TLS 1.3 stack requires 50-100 KB of RAM — exceeding the total RAM budget of most IPGs. This is why neurostimulators typically use lightweight cryptographic protocols (e.g., AES-128-CCM, custom authenticated encryption) rather than standard TLS.

### 2.4 Execution Time Budget

Real-time deadlines further constrain firmware design. A typical time budget for a closed-loop DBS system operating at a 100 Hz control rate:

| Task | Deadline | Typical Duration | Margin |
|---|---|---|---|
| Stimulation pulse generation | 10 us (per pulse) | 2 us | 80% |
| ADC read + DMA transfer | 100 us | 30 us | 70% |
| DSP processing (filter + feature) | 5 ms | 3 ms | 40% |
| Closed-loop control computation | 5 ms | 1 ms | 80% |
| Wireless command processing | 50 ms | 5 ms | 90% |
| Safety monitor check | 1 ms | 0.1 ms | 90% |

**Security implication:** Security checks must fit within these time budgets. A cryptographic signature verification (ECDSA P-256) takes approximately 10-50 ms on a Cortex-M4 — consuming the entire wireless command processing budget. This forces designers to choose between fast, insecure processing and slow, secure processing, with patient safety potentially affected by either choice.

## 3. ARM Cortex-M for Neurostimulators

### 3.1 Why Cortex-M?

The ARM Cortex-M family (M0+, M3, M4, M33) dominates the neurostimulator MCU market for several reasons:

- **Energy efficiency:** Cortex-M4 achieves 0.12 mW/MHz, critical for battery-powered implants.
- **DSP extensions:** The Cortex-M4F includes hardware floating-point and SIMD instructions (MAC, saturating arithmetic) that accelerate DSP operations by 5-10x over integer-only implementations.
- **Determinism:** Fixed interrupt latency (12 cycles for Cortex-M3/M4) enables precise timing for stimulation pulses.
- **MPU support:** The Memory Protection Unit provides hardware-enforced memory isolation between subsystems.
- **TrustZone (M33):** Hardware-enforced secure/non-secure world separation for sensitive operations.
- **Ecosystem:** Extensive toolchain support (GCC, LLVM, Keil), debug infrastructure, and verified peripheral libraries.

### 3.2 Cortex-M Memory Map

The Cortex-M memory map is fixed by the architecture and defines the address spaces that firmware operates within:

```
0xFFFFFFFF ┌─────────────────────────┐
           │  System Peripherals     │  (NVIC, SysTick, SCB, MPU)
0xE0000000 ├─────────────────────────┤
           │  External RAM/Devices    │  (AFE, RF, Stim ASIC registers)
0xA0000000 ├─────────────────────────┤
           │  External Devices        │  (Memory-mapped peripherals)
0x60000000 ├─────────────────────────┤
           │  Peripheral Region       │  (Private peripheral bus)
0x40000000 ├─────────────────────────┤
           │  SRAM                    │  (On-chip data memory)
0x20000000 ├─────────────────────────┤
           │  Code / Flash            │  (Executable memory)
0x00000000 └─────────────────────────┘
```

**Security implication:** The fixed memory map means that peripheral register addresses are known and predictable. An attacker who achieves code execution can directly access AFE, RF, and stimulation circuitry registers by writing to their memory-mapped addresses. The MPU (Memory Protection Unit) is the primary defense against unauthorized peripheral access, but MPU configuration is itself stored in memory and can be modified by an attacker who achieves sufficient privilege.

### 3.3 Exception and Interrupt Model

Cortex-M uses a unified exception/interrupt model with fixed priority levels:

- **NMI (Priority -2):** Non-maskable interrupt, used for the highest-priority safety events (e.g., watchdog timeout, brown-out detection).
- **HardFault (Priority -1):** Triggered by division by zero, unaligned access, invalid memory access, or stack overflow. This is the last resort before processor reset.
- **SVCall, PendSV, SysTick:** System service calls, context switching, and system timers.
- **Device interrupts (Priorities 0-255):** Configurable for peripheral interrupts (ADC completion, RF receive, timer expiration).

**Security implication:** The interrupt vector table is stored at address 0x00000000 (or remapped to flash). An attacker who can write to this address can redirect any interrupt handler to arbitrary code — a technique called "vector table hijacking." If the vector table is in flash (read-only), this attack requires a firmware modification. If the vector table is remapped to RAM (for dynamic interrupt handling), it becomes writable and the attack requires only a write to RAM.

### 3.4 MPU Configuration

The Cortex-M MPU allows firmware to define up to 16 memory regions (8 on M0+/M3) with independent access permissions:

| Permission | Description |
|---|---|
| No access | Any access triggers a MemManage fault |
| Read-only | Writes trigger a fault |
| Read-write | Full access |
| Execute never (XN) | Code cannot be executed from this region |
| Privileged only | Unprivileged code cannot access |

**Ideal security configuration:** Separate the firmware into privilege domains:
1. Safety monitor code: privileged, read-only, execute-only
2. Stimulation driver: privileged, read-write, execute
3. DSP code: unprivileged, read-only (code), read-write (data buffers)
4. Wireless stack: unprivileged, isolated data region
5. Diagnostic logger: unprivileged, isolated data region

**Reality:** Many neurostimulator firmware images run entirely in privileged mode with the MPU either disabled or minimally configured. This is a legacy of older Cortex-M0/M0+ devices that lacked an MPU, and of development teams prioritizing functionality over security. VIREON's firmware validation should check MPU configuration as a first-order security indicator.

## 4. RTOS for Implantable Devices

### 4.1 RTOS vs. Bare-Metal

Neurostimulator firmware can be structured as bare-metal (super-loop) or RTOS-based:

**Bare-metal (super-loop):** A single `while(1)` loop processes tasks in sequence, with interrupt service routines (ISRs) handling time-critical events. Simple, deterministic, minimal overhead. But: no memory protection between tasks, no priority-based preemption, difficult to add new features without breaking timing.

**RTOS:** A real-time operating system provides task scheduling, inter-task communication (queues, semaphores), memory management, and timing services. More complex, higher overhead, but enables modular architecture and memory isolation.

Most modern neurostimulators use a small RTOS (FreeRTOS, SafeRTOS, ThreadX, or a custom RTOS). The choice of RTOS has direct security implications:

| RTOS | Safety Certification | Memory Protection | Security Features | Used In |
|---|---|---|---|---|
| FreeRTOS | Not certified | Minimal | Optional MPU support | Research prototypes |
| SafeRTOS | IEC 61508 SIL 3 | Task isolation | Configurable permissions | Some commercial IPGs |
| ThreadX | DO-178C (avionics) | Memory protection | Security middleware available | Medtronic devices (reported) |
| Custom | Varies | Varies | Varies | Most proprietary IPGs |

### 4.2 Task Architecture

A typical RTOS task architecture for a closed-loop DBS system:

```
Priority 7 (Highest):  Safety Monitor Task
                        - Runs every 1 ms
                        - Checks: stim parameters, battery, temperature
                        - Can halt stimulation independently

Priority 6:            Stimulation Task
                        - Generates stimulation pulses
                        - Real-time deadline: < 10 us per pulse

Priority 5:            Signal Acquisition Task
                        - Reads ADC via DMA
                        - Manages sample buffers
                        - Triggers DSP processing

Priority 4:            DSP Processing Task
                        - Runs NL-002's processing pipeline
                        - Extracts features, computes band power
                        - Updates shared state for controller

Priority 3:            Closed-Loop Controller Task
                        - Reads features from DSP task
                        - Computes control output
                        - Updates stimulation parameters

Priority 2:            Wireless Communication Task
                        - Handles MICS/BLE protocol
                        - Processes incoming commands
                        - Manages outbound telemetry

Priority 1 (Lowest):   Diagnostic/Logging Task
                        - Stores diagnostic data
                        - Runs self-tests
                        - Battery monitoring
```

**Security implication:** The task priority hierarchy defines which tasks can starve which other tasks. The safety monitor MUST have the highest priority to ensure it can always intervene. But if the safety monitor has the highest priority AND contains a bug that causes it to loop indefinitely (e.g., a corrupted data structure causing an infinite iteration), it will starve ALL other tasks — including the stimulation task — causing complete therapy cessation. This is a safety-security tension: the safety monitor must be both powerful enough to halt unsafe stimulation and robust enough to never halt safe stimulation.

### 4.3 Inter-Task Communication Security

Tasks communicate through shared memory, queues, and semaphores. Each communication mechanism has security implications:

**Shared memory (globals):** The DSP task writes band power values to a global variable that the closed-loop controller reads. If the controller reads the variable while the DSP task is writing it (race condition), the controller may read a partially-updated value — a torn read that could cause an incorrect control decision. Mitigation: atomic operations, double-buffering, or mutex-protected access. In security terms, a race condition in the control loop is an integrity attack vector.

**Message queues:** The wireless task receives commands and places them on a queue for the therapy manager task. If the queue is unbounded, an attacker who floods the wireless interface can exhaust memory (queue-based DoS). If the queue is bounded with overflow discard, an attacker can cause command loss ( selective DoS). If the queue is bounded with overflow overwrite, an attacker can overwrite pending legitimate commands.

**Semaphores/Mutexes:** Protect shared resources. Priority inversion occurs when a low-priority task holds a mutex needed by a high-priority task. If an attacker can cause a low-priority task (e.g., diagnostic logger) to hold a mutex for an extended period, the high-priority safety monitor may be blocked. This is the classic priority inversion problem, infamously demonstrated in the Mars Pathfinder mission.

## 5. Memory Layout and Firmware Image Structure

### 5.1 Flash Memory Layout

A typical IPG firmware image in flash memory:

```
0x08000000 ┌──────────────────────────┐
            │  Vector Table (192 bytes) │  Interrupt handlers
0x080000C0 ├──────────────────────────┤
            │  ROM Bootloader (4-8 KB)  │  Factory-programmed, immutable
0x08002000 ├──────────────────────────┤
            │  Application Firmware    │  Updatable via OTA
            │  (200-800 KB)            │
            │  ┌────────────────────┐  │
            │  │ .text (code)       │  │
            │  │ .rodata (consts)   │  │
            │  │ .data (init vars)  │  │  (copied to SRAM at boot)
            │  └────────────────────┘  │
0x080C0000 ├──────────────────────────┤
            │  Firmware Metadata (1 KB) │  Version, hash, signature
0x080C0400 ├──────────────────────────┤
            │  Calibration Data (4 KB) │  Per-device calibration constants
0x080C1400 ├──────────────────────────┤
            │  OTA Update Buffer       │  Holds incoming firmware image
            │  (200-800 KB)            │  during OTA update
0x080F0000 └──────────────────────────┘
```

**Security implications:**
- The vector table at the base of flash is the first thing the processor reads after reset. If an attacker can modify even one entry (e.g., the HardFault handler), they gain control of the processor's error handling path.
- The bootloader is the trust anchor. If it is in ROM (true ROM, not flash), it cannot be modified. If it is in flash, it is vulnerable to the same attacks as the application firmware.
- The OTA update buffer must be large enough to hold a complete firmware image. This means the flash must have spare capacity equal to the firmware size — effectively doubling the flash requirement.
- Calibration data is device-specific and may contain information useful for attacking the device (e.g., AFE gain settings, RF frequency calibration). Exfiltrating this data enables targeted attacks.

### 5.2 SRAM Layout

```
0x20000000 ┌──────────────────────────┐
            │  Stack (Main)             │  Grows downward
            │  ↓                        │
            │                           │
            ├──────────────────────────┤
            │  Stack (Interrupts)       │  Separate stack for ISR context
            │  ↓                        │
            │                           │
0x20001C00 ├──────────────────────────┤
            │  .data / .bss             │  Global variables
0x20002000 ├──────────────────────────┤
            │  Signal Buffers           │  Circular buffers for ADC samples
            │  (16-32 KB)              │  Most SRAM-consuming subsystem
0x20008000 ├──────────────────────────┤
            │  DSP Buffers              │  FFT input/output, filter state
            │  (8-16 KB)               │
0x2000C000 ├──────────────────────────┤
            │  RTOS Structures          │  Task control blocks, queues
            │  (4-8 KB)                │
0x2000E000 ├──────────────────────────┤
            │  Heap                     │  Dynamic allocation (if used)
            │  (4-16 KB)               │  Often avoided in safety-critical code
0x20010000 └──────────────────────────┘
```

**Security implications:**
- Stack overflow: If the main stack or interrupt stack grows beyond its allocated region, it overwrites adjacent memory — potentially corrupting signal buffers, DSP state, or RTOS structures. Stack canaries (compiler-inserted integrity checks) can detect stack overflow but are not universally used in medical firmware.
- Signal buffers are the largest SRAM consumers and are often implemented as circular buffers. A buffer overflow in signal processing (e.g., writing more samples than the buffer can hold) overwrites adjacent DSP or RTOS memory. This is the most common memory corruption vector in neurostimulator firmware.
- The heap is often disabled entirely in safety-critical firmware (static allocation only). If the heap is used, heap corruption (use-after-free, double-free, buffer overflow) is a severe vulnerability. Memory allocators for medical devices should use pool-based allocation with per-pool size limits.

### 5.3 Firmware Image Format

Firmware images for OTA update typically have a structured format:

```
┌──────────────────────────────────┐
│  Header (32 bytes)               │
│  - Magic number (4 bytes)        │
│  - Version (4 bytes)             │
│  - Image size (4 bytes)          │
│  - Hardware revision (2 bytes)   │
│  - Image type (1 byte)           │
│  - Flags (1 byte)                │
│  - Reserved (16 bytes)           │
├──────────────────────────────────┤
│  Cryptographic Signature (64 B)  │  ECDSA P-256 or RSA-2048
├──────────────────────────────────┤
│  Firmware Binary (N bytes)       │
├──────────────────────────────────┤
│  Metadata (variable)             │
│  - Build timestamp               │
│  - Git commit hash               │
│  - Component versions            │
│  - SHA-256 hash of binary        │
└──────────────────────────────────┘
```

**Security implications:** The signature covers the firmware binary but must also cover the header and metadata. If the signature only covers the binary, an attacker can modify the header (e.g., change the version number to trigger a rollback to an older, vulnerable firmware) without invalidating the signature. The VIREON firmware validator should verify that the signature covers all mutable fields.

## 6. Secure Boot Chain

### 6.1 Boot Sequence

The secure boot chain for a neurostimulator proceeds through multiple stages, each verifying the next:

```
Power-On Reset
    │
    v
[Stage 0: ROM Bootloader]  ← Hardware root of trust
    │  - Immutable (true ROM)
    │  - Verifies Stage 1 hash against OTP-fused hash
    │  - Cannot be updated
    v
[Stage 1: Flash Bootloader]  ← Updatable, but verified by Stage 0
    │  - Handles OTA update logic
    │  - Verifies Stage 2 signature
    │  - Manages firmware image selection (A/B partition)
    │  - Can be updated via signed OTA
    v
[Stage 2: Application Firmware]  ← Updatable, verified by Stage 1
    │  - RTOS initialization
    │  - Task creation and scheduling
    │  - Peripheral initialization
    │  - Enters normal operation
    v
[Normal Operation]
```

### 6.2 Trust Anchors

The secure boot chain relies on trust anchors — values that are trusted because they cannot be modified:

1. **ROM bootloader hash:** Fused into one-time programmable (OTP) memory during manufacturing. The ROM bootloader's hash is computed at manufacturing time and stored in OTP. At boot, the processor computes the ROM bootloader's hash and compares it to the OTP value. If they don't match, the device halts.

2. **Flash bootloader public key:** Stored in OTP or in a protected flash region. The Stage 0 bootloader uses this public key to verify the Stage 1 bootloader's signature.

3. **Application firmware public key:** Either the same as the bootloader public key (simpler) or a different key (more flexible but requires key management). Used by the Stage 1 bootloader to verify the application firmware.

**Security analysis:** The entire chain's security depends on the OTP fuses. If OTP fuses can be read out through a side-channel attack (e.g., optical probing of the die), the root of trust is compromised. If the manufacturer uses the same signing key for all devices (common for cost reasons), compromising one device's key compromises all devices. Per-device keys provide stronger security but complicate the signing and update infrastructure.

### 6.3 A/B Partitioning

To prevent bricking during OTA updates, many neurostimulators use A/B partitioning:

```
Flash Layout with A/B Partitions:

┌──────────────┐
│  Bootloader  │  (shared, verified by ROM)
├──────────────┤
│  Partition A │  ← Currently running firmware
│  (active)    │
├──────────────┤
│  Partition B │  ← Staging area for next update
│  (inactive)  │
├──────────────┤
│  Shared Data │  ← Calibration, persistent settings
└──────────────┘
```

The update process:
1. New firmware is written to the inactive partition (B)
2. The bootloader verifies the new firmware's signature
3. If verification passes, the active partition flag is flipped (A→B)
4. On next reboot, the device boots from the new partition
5. If the new firmware fails to start (watchdog timeout), the bootloader rolls back to the previous partition

**Security implication:** A/B partitioning provides rollback protection but also creates a rollback attack surface. An attacker who can modify the partition selection flag can force the device to boot an older firmware version with known vulnerabilities — a version rollback attack. Mitigation: a monotonic version counter stored in OTP that can only be incremented, never decremented. The bootloader verifies that the new firmware's version is strictly greater than the current version.

### 6.4 Boot Chain Vulnerabilities

Known vulnerability classes in secure boot chains:

1. **Signature verification bypass:** A bug in the cryptographic verification code that accepts invalid signatures. Demonstrated in multiple consumer IoT devices where the verification function returns success without actually checking the signature (e.g., `if (verify_signature(image, sig)) { /* boot */ } else { /* also boot */ }`).

2. **Downgrade attack:** No version enforcement allows installing an older firmware with known vulnerabilities. The monotonic counter mitigation requires OTP storage and careful implementation.

3. **Time-of-check-to-time-of-use (TOCTOU):** The bootloader verifies the firmware image, then boots it. If the image can be modified between verification and execution (e.g., through DMA), the verification is meaningless. Mitigation: verify the image immediately before jumping to it, or use XN (execute-never) protection on the flash region until verification is complete.

4. **Bootloader deserialization attack:** If the bootloader parses complex data structures (firmware manifest, metadata) before verification, a malicious manifest can exploit parsing vulnerabilities. Mitigation: verify the signature FIRST, then parse.

## 7. Communication Stack Firmware

### 7.1 Protocol Stack Architecture

The wireless communication firmware implements the protocol stack that handles all communication between the IPG and the external programmer/clinic system:

```
┌─────────────────────────────────┐
│  Application Protocol Layer     │  Therapy commands, parameter sets
│  (Custom, proprietary)          │
├─────────────────────────────────┤
│  Security Layer                 │  Encryption, authentication, integrity
│  (AES-CCM, ECDSA)               │
├─────────────────────────────────┤
│  Transport Layer                │  Packet segmentation, reassembly
│  (Custom)                       │  Acknowledgment, retry
├─────────────────────────────────┤
│  MAC Layer                      │  Framing, CRC, addressing
│  (Custom or 802.15.6-based)     │
├─────────────────────────────────┤
│  Physical Layer Driver          │  MICS transceiver control
│  (Register-level)               │  Frequency, power, modulation
└─────────────────────────────────┘
```

**Security implication:** Each layer adds parsing and state management code. Each parser is a potential attack surface. The application protocol layer is particularly dangerous because it handles the highest-level commands (e.g., "change stimulation amplitude to 5 mA"). A parsing vulnerability at this layer directly controls the device's clinical behavior.

### 7.2 Command Processing Pipeline

When the IPG receives a wireless command, the firmware processes it through the following pipeline:

1. **RF receive interrupt:** The RF transceiver signals data arrival via interrupt.
2. **DMA transfer:** Received bytes are transferred to a buffer in SRAM via DMA.
3. **CRC check:** The MAC layer verifies the packet integrity using CRC-16 or CRC-32.
4. **Decryption:** The security layer decrypts the payload using the session key.
5. **Authentication:** The security layer verifies the packet's authentication tag.
6. **Deserialization:** The transport layer parses the packet structure (header, payload, footer).
7. **Command parsing:** The application layer extracts the command type and parameters.
8. **Authorization:** The application layer verifies that the sender is authorized to execute this command.
9. **Parameter validation:** The application layer validates the command parameters against safety limits.
10. **Execution:** The command is executed (stimulation parameter change, diagnostic request, etc.).
11. **Response:** A response packet is constructed, encrypted, authenticated, and transmitted.

**Security analysis:** Each step introduces potential vulnerabilities:
- Step 2: DMA to a fixed-size buffer without bounds checking → buffer overflow.
- Step 3: CRC is not a security mechanism (it provides error detection, not authentication). An attacker with knowledge of the CRC algorithm can craft packets with valid CRCs.
- Step 4-5: If the session key is weak or reused, cryptographic attacks apply.
- Step 6: Deserialization of complex structures is a notorious source of vulnerabilities (type confusion, integer overflow, null pointer dereference).
- Step 7: If the command parser does not handle all possible command types, unknown commands may fall through to a default handler with unexpected behavior.
- Step 8: If authorization is based on a single shared secret (common in legacy devices), compromise of the secret enables unauthorized command execution.
- Step 9: If parameter validation has gaps (e.g., no upper bound on stimulation amplitude), unsafe parameters reach the stimulation hardware.

### 7.3 Session Management

Wireless communication sessions in neurostimulators follow a typical pattern:

1. **Pairing:** The IPG and programmer establish a shared secret (done once, during implantation or clinic visit). The pairing secret is stored in both devices.
2. **Session establishment:** The programmer initiates a session by sending a session request. The IPG responds with a challenge. The programmer proves knowledge of the pairing secret by responding to the challenge.
3. **Session key derivation:** Both sides derive a session key from the pairing secret and random nonces using a KDF (e.g., HKDF-SHA256).
4. **Encrypted communication:** All subsequent packets are encrypted and authenticated using the session key.
5. **Session termination:** Either side can terminate the session. The session key is discarded.

**Security implication:** The pairing secret is the most sensitive cryptographic material in the system. If the pairing secret is extracted from the programmer device (through malware, lost device, or reverse engineering), an attacker can establish sessions with the IPG. If the pairing secret is stored in plaintext in the IPG's flash, it can be extracted through firmware dump (if the attacker gains read access to flash). Mitigation: store the pairing secret in a hardware security module (HSM) or in a special-purpose register that is not directly readable.

## 8. Stimulation Pulse Generation Firmware

### 8.1 Pulse Generation Architecture

The stimulation firmware controls the delivery of electrical pulses to neural tissue. The precision and safety of this subsystem directly determines the device's therapeutic efficacy and safety profile.

```
┌─────────────────────────────────┐
│  Stimulation Parameter Table     │  Current amplitude, pulse width,
│  (SRAM, protected)              │  frequency, electrode config
├─────────────────────────────────┤
│  Pulse Sequencer                │  Generates timing for each pulse
│  (Timer peripheral or DMA)      │  based on parameter table
├─────────────────────────────────┤
│  Current Source Driver          │  Controls actual current delivery
│  (DAC + current mirror)         │  via the stimulation ASIC
├─────────────────────────────────┤
│  Impedance Measurement          │  Measures electrode-tissue impedance
│  (Periodic, between pulses)     │  for safety monitoring
└─────────────────────────────────┘
```

### 8.2 Stimulation Parameter Safety Limits

The firmware enforces safety limits on stimulation parameters. These limits are typically hardcoded constants that define the absolute maximum safe values for each parameter:

| Parameter | Typical Range | Absolute Maximum | Safety Rationale |
|---|---|---|---|
| Amplitude | 0-10 mA | 10.5 mA | Tissue damage above ~15 mA |
| Pulse width | 60-450 us | 500 us | Charge density limits |
| Frequency | 1-185 Hz | 200 Hz | Tissue heating, seizure risk |
| Duty cycle | Continuous/intermittent | 100% | Charge accumulation |

**Security implication:** These safety limits are the last line of defense between the firmware and the stimulation hardware. If an attacker can modify these limits (by patching the firmware or by exploiting a parameter validation gap), they can deliver stimulation that exceeds safe levels. The safety monitor (Section 15) provides a backup check, but if both the parameter validation and the safety monitor are compromised, there is no remaining defense.

### 8.3 Stimulation Timing Precision

Stimulation pulses must be delivered with precise timing. The timing is generated by hardware timers that are programmed by the firmware:

- **Cathodic phase:** Current flows from the electrode into the tissue. Duration: 60-450 us.
- **Interphase delay:** No current flows. Duration: 0-100 us. Prevents net DC charge.
- **Anodic phase:** Current flows from the tissue to the electrode (reversal). Duration: equal to or greater than cathodic phase for charge balance.
- **Inter-pulse interval:** No current flows. Duration: determined by frequency (e.g., 5.4 ms for 185 Hz).

**Security implication:** The timing parameters are programmed into hardware timer registers. If the firmware writes incorrect values to these registers (due to a bug or an attack), the resulting stimulation waveform may not be charge-balanced, leading to electrochemical damage at the electrode-tissue interface. The charge balance check is typically performed by the safety monitor, but if the safety monitor is also compromised, the damage may go undetected.

### 8.4 Firmware-to-Hardware Interface

The firmware controls the stimulation hardware through memory-mapped registers:

```c
// Simplified register map for stimulation ASIC
#define STIM_CTRL       (*(volatile uint32_t *)0x40001000)  // Control register
#define STIM_AMPLITUDE  (*(volatile uint32_t *)0x40001004)  // Amplitude (uA)
#define STIM_PW_CATH    (*(volatile uint32_t *)0x40001008)  // Cathodic pulse width (us)
#define STIM_PW_ANOD    (*(volatile uint32_t *)0x4000100C)  // Anodic pulse width (us)
#define STIM_FREQ       (*(volatile uint32_t *)0x40001010)  // Frequency (Hz)
#define STIM_ELECTRODE  (*(volatile uint32_t *)0x40001014)  // Electrode configuration
#define STIM_STATUS     (*(volatile uint32_t *)0x40001018)  // Status register
```

**Security implication:** These register addresses are fixed and documented (or can be discovered through reverse engineering). Any code running on the MCU can write to these registers. The MPU should restrict access to the stimulation register region to privileged code only, but as noted in Section 3.4, MPU configuration is often inadequate. VIREON's firmware validation should verify that stimulation register access is properly restricted.