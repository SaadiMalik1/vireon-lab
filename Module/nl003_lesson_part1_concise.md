# NL-003: Neurostimulator Firmware Architecture (Part 1)

## 1. Overview

The firmware running inside an implantable pulse generator is the most security-critical and least accessible component of a neurotechnology system. It is security-critical because it directly controls electrical stimulation of neural tissue — a firmware bug or compromise can cause direct patient harm. It is the least accessible because it runs on a processor sealed inside a titanium case implanted in the patient's body, with no external debug interface, no logging, and no direct observation capability.

This module teaches you to analyze this firmware through its external manifestations: the binary image (if obtainable), the observable behavior (through telemetry), and the known architecture of the target platform. The analysis methodology mirrors real-world medical device security research where firmware is extracted through supply chain access, regulatory submissions, or reverse engineering of update packages.

## 2. IPG Hardware Platform Reference

### 2.1 Typical MCU Architecture

Most commercial neurostimulators use ARM Cortex-M class processors. The specific choice has direct security implications:

**ARM Cortex-M0/M0+:** Minimalist core. No MPU (Memory Protection Unit). No hardware divide. No floating-point unit. Single-cycle I/O. Used in older or cost-optimized designs. **Security implication: no MPU means no hardware memory protection — firmware bugs in the telemetry handler can overwrite stimulation code.**

**ARM Cortex-M3:** Includes MPU with up to 8 regions, hardware divide, single-cycle multiply. No FPU. Used in mid-range devices. **Security implication: MPU enables memory protection, but only if configured correctly by the firmware. Misconfiguration is common.**

**ARM Cortex-M4:** Includes MPU, FPU (single-precision), DSP extensions (saturated math, SIMD). Used in higher-performance devices (closed-loop DBS, high-channel BCIs). **Security implication: FPU enables more complex signal processing, increasing the attack surface of the DSP code.**

**ARM Cortex-M33 (TrustZone for M):** Includes MPU, FPU, and TrustZone — hardware partitioning into Secure and Non-Secure worlds. Used in newer security-conscious designs. **Security implication: TrustZone provides strong hardware isolation between security-critical and non-security-critical code, but the partitioning must be correctly designed.**

### 2.2 Memory Map

A typical IPG memory map (Cortex-M4, 1 MB flash, 256 KB SRAM):

```
+--------------------------------------------------+ 0x20040000
|                    SRAM (256 KB)                  |
|  +----------------------------------------------+|
|  | Stack (grows down from top)                   ||
|  +----------------------------------------------+|
|  | Heap (grows up from BSS end)                   ||
|  +----------------------------------------------+|
|  | .bss (zeroed data)                            ||
|  +----------------------------------------------+|
|  | .data (initialized data, copied from flash)   ||
|  +----------------------------------------------+|
|  0x20000000
+--------------------------------------------------+
|         Peripheral Registers (memory-mapped I/O)  |
|  0x40000000 - 0x5FFFFFFF                          |
+--------------------------------------------------+
|                    Flash (1 MB)                    |
|  +----------------------------------------------+|
|  | Firmware signature / root of trust             || 0x080FFF00
|  +----------------------------------------------+|
|  | Firmware metadata (version, build, device ID)  || 0x080FF800
|  +----------------------------------------------+|
|  | Application firmware                           || 0x08008000
|  |   - Telemetry protocol handler                 ||
|  |   - Signal processing (DSP)                    ||
|  |   - Stimulation controller                      ||
|  |   - Closed-loop algorithm                      ||
|  |   - Safety monitor (or reference to HW)        ||
|  |   - Clinical state machine                      ||
|  +----------------------------------------------+|
|  | Bootloader (8-32 KB)                           || 0x08000000
|  +----------------------------------------------+|
|  | Vector table (first 256+ bytes)                ||
|  +----------------------------------------------+|
|  0x08000000
+--------------------------------------------------+
|         System ROM (vendor-specific)               |
|  0x00000000 - 0x1FFFFFFF
+--------------------------------------------------+
```

**Security-critical memory regions:**

1. **Vector table (0x08000000):** The first entry is the initial stack pointer. The second entry is the reset handler address. If an attacker can modify the vector table, they can redirect execution to arbitrary code. The vector table location is controlled by the VTOR register — if VTOR is not locked, it can be modified at runtime.

2. **Bootloader (0x08000000-0x08008000):** Responsible for firmware verification and update. If the bootloader is compromised, all subsequent security is irrelevant. The bootloader should be the smallest, most carefully reviewed code in the firmware.

3. **Firmware signature (near end of flash):** Contains the cryptographic signature of the application firmware. The bootloader reads this signature and verifies it before executing the application. The signature must be stored in a region that the application cannot overwrite — typically in a separate flash sector with write protection.

4. **Stimulation parameter memory:** Contains the current therapy parameters (voltage, frequency, pulse width, electrode configuration). This data must be integrity-protected because corruption directly affects stimulation delivery. In some devices, this is stored in a separate non-volatile memory (EEPROM or dedicated flash sector) with hardware write protection.

### 2.3 Peripheral Security Relevance

ARM Cortex-M peripherals are memory-mapped. Writing to a peripheral register has immediate hardware effects. This creates a direct path from firmware bugs to physical effects:

- **GPIO registers:** Control electrode switching (which contacts are active). A write to the wrong GPIO register could connect the stimulation circuitry to the wrong electrodes.

- **Timer registers:** Control stimulation pulse timing. A write to the wrong timer register could change the pulse width or frequency beyond safe limits.

- **DAC registers:** Control stimulation amplitude. A write to the wrong DAC register could deliver excessive current.

- **ADC registers:** Control neural signal acquisition. A write to the wrong ADC register could change the gain or sampling rate, affecting signal quality.

- **SPI/I2C registers:** Communicate with the RF module. A write to the wrong SPI register could transmit arbitrary data over the wireless link (information disclosure).

The safety monitor provides hardware-level protection against some of these (it monitors DAC output, not DAC register writes), but not all. The MPU provides software-level protection by restricting which code can access which peripheral regions. VIREON's firmware analysis must verify both protection layers.

## 3. Boot Sequence and Secure Boot

### 3.1 ARM Cortex-M Boot Process

When an IPG powers on (battery connection, reset, or watchdog timeout), the following sequence occurs:

1. **Hardware reset:** The processor core resets all registers to default values. The PC is set to 0x00000000 (address 0 in the system memory map, which is aliased to the flash base address, typically 0x08000000).

2. **Vector table fetch:** The processor reads the initial stack pointer from address 0x08000000 and the reset handler address from 0x08000004.

3. **Reset handler execution:** The code at the reset handler address begins executing. In a typical IPG, the reset handler is part of the bootloader.

4. **Bootloader execution:** The bootloader performs hardware initialization, verifies the application firmware, and transfers control to the application.

5. **Application execution:** The application firmware initializes the signal processing pipeline, configures the wireless interface, and enters the main loop.

### 3.2 Bootloader Responsibilities

The bootloader is the root of trust. Its responsibilities from a security perspective:

1. **Hardware initialization:** Configure clock, memory, and essential peripherals. Must configure the MPU before enabling any peripherals that could be exploited.

2. **Firmware integrity verification:** Read the application firmware's cryptographic signature and verify it against the embedded verification key. If verification fails, do not execute the application.

3. **Firmware update handling:** If a firmware update is pending (triggered during the previous programming session), verify the new firmware before replacing the old one. Implement atomic update (write new firmware to a backup region, verify, then swap the active region pointer).

4. **Watchdog configuration:** Enable the independent hardware watchdog before transferring control to the application. The watchdog ensures that if the application hangs, the device resets and the bootloader regains control.

5. **Control transfer:** Jump to the application's entry point. This must be an atomic operation — the bootloader should not leave any state that the application could exploit.

### 3.3 Secure Boot Implementation Levels

**Level 0 — No secure boot:** The bootloader does not verify the application firmware. It simply jumps to the application's entry point. Any firmware modification (through an update vulnerability or direct flash write) will be executed. This is the state of most legacy implantable devices.

**Level 1 — Simple hash check:** The bootloader computes a hash (SHA-256) of the application firmware and compares it against a stored reference hash. Protection: detects accidental corruption. Does not detect intentional modification (the attacker can replace both the firmware and the hash).

**Level 2 — Asymmetric signature verification:** The bootloader verifies an RSA or ECDSA signature over the application firmware using an embedded public key. The private key is held by the manufacturer. Protection: detects any firmware modification. The attacker cannot forge a valid signature without the private key.

**Level 3 — Certificate chain:** The bootloader verifies a certificate chain: manufacturer CA certificate → device certificate → firmware signature. Enables per-device or per-batch signing. Protection: enables revocation of compromised signing keys.

**Level 4 — Hardware root of trust:** The verification key is stored in a hardware security element (e.g., ARM TrustZone secure storage, dedicated crypto accelerator with key storage, or one-time-programmable fuses). The key cannot be extracted even with physical access to the chip. Protection: the highest level of firmware integrity assurance.

### 3.4 Secure Boot Vulnerabilities

**Signature bypass via bootloader bug:** If the bootloader has a buffer overflow, it can be exploited to skip the signature check and execute arbitrary firmware. The bootloader is typically smaller and simpler than the application, but it is also the only code that runs with full hardware access before the MPU is configured.

**Rollback attack:** If the bootloader does not enforce a minimum firmware version, an attacker can install an older, known-vulnerable firmware version. The bootloader verifies the signature (the old firmware is legitimately signed), but the installed version has known vulnerabilities.

**Downgrade protection:** Implement an anti-rollback counter — a monotonic counter stored in one-time-programmable memory that is incremented with each firmware update. The bootloader refuses to load firmware with a version number lower than the stored counter.

**Key extraction:** If the verification key is stored in regular flash (not hardware-protected), it can be extracted through firmware analysis or physical attack (chip decapping, side-channel analysis). Once extracted, the attacker can sign arbitrary firmware.

**VTOR manipulation:** If the VTOR (Vector Table Offset Register) is not locked after boot, the application firmware could modify VTOR to point to a malicious vector table, redirecting interrupt handling to attacker-controlled code. The bootloader should lock VTOR before transferring control.

## 4. RTOS vs. Bare-Metal

### 4.1 Architectural Choice

IPG firmware can be structured as bare-metal (super-loop) or RTOS-based:

**Bare-metal (super-loop):**
```
int main() {
    hardware_init();
    while (1) {
        process_telemetry();      // Non-blocking
        acquire_neural_data();    // Non-blocking
        run_signal_processing(); // Non-blocking
        update_stimulation();     // Non-blocking
        check_safety();           // Non-blocking
        enter_low_power_mode();   // Sleep until next interrupt
    }
}
```

Pros: Simple, predictable timing, minimal RAM overhead, no context switching vulnerabilities.
Cons: Harder to add features, no task isolation, telemetry processing can block signal processing.

**RTOS (e.g., FreeRTOS, ThreadX, Zephyr):**
```
Tasks: telemetry_task, signal_processing_task, 
       stimulation_task, safety_monitor_task

Priority ordering: safety_monitor > stimulation > signal_processing > telemetry
```

Pros: Clean task separation, priority-based scheduling, easier to maintain and extend.
Cons: Context switching overhead, RAM overhead (stack per task), RTOS itself has an attack surface.

### 4.2 Security Implications

The choice between bare-metal and RTOS has security implications:

**Task isolation (RTOS advantage):** With an MPU-configured RTOS, the telemetry task and the stimulation task can be placed in separate MPU regions. A buffer overflow in the telemetry handler cannot corrupt the stimulation task's memory. With bare-metal, a single address space means any bug can affect any part of the system.

**Priority inversion (RTOS vulnerability):** If the RTOS priority assignment is incorrect, a low-priority telemetry task could block a high-priority safety task through shared resource contention. This is the classic priority inversion problem (famously caused the Mars Pathfinder failure). In a neurostimulator, priority inversion could delay a safety check, allowing out-of-spec stimulation to persist longer than intended.

**Timing predictability (bare-metal advantage):** In a super-loop, the execution order is deterministic. In an RTOS, task scheduling depends on interrupt timing, which can be influenced by an attacker who controls the wireless interface (by sending packets at specific times). This makes RTOS-based systems harder to validate for timing security.

**RTOS-specific vulnerabilities:** The RTOS kernel itself has had vulnerabilities (e.g., FreeRTOS heap management bugs, Zephyr kernel memory corruption). Using an RTOS introduces a third-party codebase that must be audited separately.

## 5. Embedded Security Features

### 5.1 Memory Protection Unit (MPU)

The ARM Cortex-M MPU allows the firmware to define up to 8 (M3/M4) or 16 (M23/M33) memory regions with independent access permissions (read, write, execute) and memory attributes (cacheable, bufferable, shareable).

**Correct MPU configuration for a neurostimulator:**

```
Region 0: Flash (application code)    — RX (read+execute, no write)
Region 1: Flash (bootloader)          — RX (read+execute, no write)
Region 2: Flash (firmware signature)  — R only (no write, no execute)
Region 3: SRAM (stack)                 — RWX (full access — unavoidable for stack)
Region 4: SRAM (signal buffers)        — RW (no execute — NX bit)
Region 5: SRAM (telemetry buffers)     — RW (no execute)
Region 6: Peripheral region            — RW (controlled by privilege level)
Region 7: System ROM                   — R only
```

**Key security configurations:**
- **Execute-never (XN) on SRAM:** Prevents code execution from RAM. This is the primary defense against code injection attacks — even if an attacker writes shellcode to SRAM (via buffer overflow), the MPU prevents execution. **This is the single most important MPU configuration for neurostimulator security.**
- **Write-protection on flash:** The application should not be able to write to its own code region. Flash write protection prevents self-modifying code and limits the impact of firmware bugs.
- **Privilege separation:** ARM Cortex-M has two privilege levels: thread (unprivileged) and handler (privileged, used by interrupt handlers). The telemetry handler should run at thread mode, while the safety monitor should run at handler mode. This prevents the telemetry handler from modifying safety-critical peripheral registers.

**MPU bypass vectors:** The vector table is in flash and is always executable. If an attacker can overwrite the vector table (via a flash write vulnerability), they can redirect any interrupt handler to their code. The vector table should be in a separate MPU region with stricter protection, or better yet, the VTOR should be locked to prevent reconfiguration.

### 5.2 Watchdog Timer

The watchdog timer is an independent hardware counter that must be periodically "fed" (reset) by the firmware. If the firmware fails to feed the watchdog within the timeout period, the watchdog generates a reset, returning control to the bootloader.

**Security configuration:**
- **Independent clock source:** The watchdog should use its own clock (not the system clock). If the system clock is manipulated, the watchdog should still timeout.
- **Short timeout:** For a safety-critical system, the watchdog timeout should be short (100-500 ms). This limits the time the system can spend in a compromised state.
- **Windowed watchdog:** An advanced watchdog that requires feeding within a specific time window (not just before timeout). Prevents an attacker from feeding the watchdog too frequently.
- **Cannot be disabled:** The watchdog enable bit should be in a one-time-programmable register. Once enabled, it cannot be disabled without a full chip reset.

**Watchdog bypass:** If the attacker can execute arbitrary code, they can feed the watchdog as part of their malicious code, preventing the watchdog from detecting the compromise. The watchdog is a defense against firmware bugs and hangs, not against determined attackers with code execution capability.

### 5.3 Debug Interface Security

ARM Cortex-M provides standardized debug access through SWD (Serial Wire Debug) and JTAG. These interfaces provide:

- **Halting the processor:** Stop execution and inspect/modify all registers and memory.
- **Breakpoints:** Set hardware breakpoints to stop execution at specific addresses.
- **Memory access:** Read and write any memory location, including flash.
- **Flash programming:** Program the flash memory through the debug interface.

**Security measures:**
- **Debug disable:** In production devices, the debug interface should be permanently disabled by blowing a fuse in the chip's debug authentication register. Once blown, SWD/JTAG access is permanently disabled.
- **Debug authentication:** Some chips support debug authentication — the debug interface is disabled by default and requires a cryptographic challenge-response to enable. The debug key is unique per device.
- **Read-out protection:** ARM provides read-out protection levels (RDP level 0, 1, 2). Level 2 permanently disables both debug access and flash read access. This is the appropriate setting for production implants.

**VIREON validation:** When analyzing a firmware image, VIREON should check for evidence of debug interface configuration. If the firmware enables or fails to disable debug access, this is a critical finding.

## 6. Interrupt Architecture and Security

### 6.1 NVIC (Nested Vectored Interrupt Controller)

The NVIC manages all interrupts on Cortex-M. Security-relevant properties:

**Priority-based preemption:** Higher-priority interrupts preempt lower-priority ones. In a neurostimulator:
- Highest priority: Safety monitor (must respond to stimulation faults immediately)
- High priority: Stimulation timer (precise pulse timing)
- Medium priority: ADC/DMA completion (neural data acquisition)
- Low priority: Telemetry received (external communication)

**Priority inversion attack:** An attacker who controls the telemetry interface can generate interrupts at a high rate, potentially starving lower-priority tasks of CPU time. If the telemetry interrupt priority is incorrectly set higher than the safety monitor priority, an attacker could prevent safety checks from executing. VIREON must verify the NVIC priority configuration.

**Interrupt stacking:** Cortex-M automatically stacks (pushes to the stack) R0-R3, R12, LR, PC, and xPSR when entering an interrupt. This creates a stack frame that contains the return address. If an attacker can overwrite the stacked PC (via a stack buffer overflow), they can redirect execution when the interrupt returns. Stack canaries and MPU-based stack protection are the primary defenses.

## 7. Power Management and Security

### 7.1 Low-Power Modes

IPG firmware spends most of its time in low-power modes to extend battery life. The transition between low-power and active modes creates a security-relevant timing window:

**Sleep mode:** CPU stops, peripherals continue. Wake on interrupt. The firmware is not executing — attacks that require active firmware execution cannot proceed.

**Deep sleep:** CPU and most peripherals stop. Only the real-time clock and wakeup sources remain active. Transition time to active mode: microseconds to milliseconds.

**Standby:** Only the backup domain (real-time clock, backup registers) remains active. Transition time: milliseconds. The RF module must re-initialize after waking, creating a longer window of vulnerability.

**Security implication of wake-up timing:** When the device wakes from deep sleep to process a telemetry packet, there is a finite time between the RF module receiving the packet and the firmware being ready to process it. During this time, the packet is buffered in the RF module's FIFO. If the FIFO is small and an attacker floods the device with packets, the FIFO can overflow, causing packet loss. This is a denial-of-service attack that exploits the power management state machine.

### 7.2 Battery Life Security Trade-off

Every millijoule spent on security is a millijoule not available for therapy. The battery budget forces explicit trade-offs:

| Operation | Energy Cost | Security Value |
|---|---|---|
| AES-128 encryption (per packet) | ~0.5 mJ | High (confidentiality) |
| ECDSA signature verification | ~5 mJ | High (firmware integrity) |
| AES-GCM (encrypt + authenticate) | ~0.8 mJ | Very high (confidentiality + integrity) |
| Random number generation | ~0.1 mJ | Medium (nonce generation) |
| Flash write (firmware update sector) | ~50 mJ | High (update integrity) |

For a non-rechargeable IPG with a 10-year battery life, the total energy budget is approximately 100-300 Joules (depending on the battery capacity and the average stimulation duty cycle). Security operations consume a fraction of this budget, but the fraction is non-trivial for power-hungry operations like ECDSA signature verification.

## 8. Communication Between Firmware Components

### 8.1 Inter-Module Communication

The IPG firmware is typically decomposed into modules with defined interfaces:

```
+------------------+     +------------------+     +------------------+
| Telemetry        |     | Signal           |     | Stimulation      |
| Handler          |<--->| Processing       |<--->| Controller       |
| (SPI/IRQ driven) |     | (Timer/DMA)      |     | (Timer driven)   |
+------------------+     +------------------+     +------------------+
         |                       |                       |
         v                       v                       v
    [Wireless Link]         [ADC + AFE]            [DAC + Electrodes]
                                                    |
                                                    v
                                             +------------------+
                                             | Safety Monitor    |
                                             | (HW, independent) |
                                             +------------------+
```

**Security-critical interfaces:**

1. **Telemetry → Signal Processing:** Received commands (parameter changes, firmware updates) must be validated before being passed to the signal processing module. The interface should include: command authentication, parameter range checking, and rate limiting.

2. **Signal Processing → Stimulation Controller:** In closed-loop systems, the computed feature values (e.g., beta power) drive the stimulation controller. The interface must include: feature range checking, rate-of-change limiting (to prevent sudden stimulation changes), and timeout detection (if features stop updating, assume the processing pipeline has failed and maintain last safe state).

3. **Any Module → Safety Monitor:** The safety monitor is not a module that other modules communicate with — it is an independent hardware circuit that monitors the stimulation output. However, the firmware must correctly configure the safety monitor's limits at startup. If the safety monitor is configurable (via memory-mapped registers), those registers must be write-protected after configuration.