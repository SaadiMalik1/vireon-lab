# NL-001: Neural Signals & The Neurosecurity Problem Space (Part 2)

## 9. System Architecture

### 9.1 Reference Architecture: Closed-Loop DBS System

The following architecture represents a state-of-the-art closed-loop DBS system (Medtronic Percept PC / Abbott Infinity as reference points), which is the most security-relevant neurotechnology system currently in clinical deployment:

```
+====================================================================+
|                         PATIENT BODY                              |
|                                                                    |
|  +------------+    +-------------------------------------------+  |
|  |  Lead      |    |              IPG                          |  |
|  | (4/8       |--->|  +--------+  +------+  +----------------+  |  |
|  |  contacts) |    |  | AFE    |->| ADC  |->| Microcontroller|  |  |
|  +------------+    |  +--------+  +------+  |  +----------+  |  |
|                    |                       |  |Closed-Loop|  |  |
|  +------------+    |                       |  |Controller |  |  |
|  |  Lead      |    |                       |  +----------+  |  |
|  | (stim      |<---|                       |  +----------+  |  |
|  |  contacts) |    |                       |  |Telemetry  |  |  |
|  +------------+    |                       |  |Handler    |  |  |
|                    |                       |  +----------+  |  |
|                    |                       |  +----------+  |  |
|                    |                       |  |Safety     |  |  |
|                    |                       |  |Monitor    |  |  |
|                    |                       |  +----------+  |  |
|                    |                       +------+-------+  |  |
|                    |                              |          |  |
|                    |                       +------v------+   |  |
|                    |                       |RF Antenna   |   |  |
|                    |                       |(MICS band)  |   |  |
|                    |                       +------+------|   |  |
|                    +------------------------------+--------+  |
+============================================================+====+
                                                   |
                                              Wireless Link
                                              (MICS 402-405 MHz)
                                                   |
+============================================================+====+
|                     CLINICIAN SIDE                          |    |
|                                                   v         |    |
|  +----------------+    +----------------------------------+  |  |
|  |  Programmer    |--->|     Clinical Programmer Tablet    |  |  |
|  |  Wand          |    |  +----------+  +---------------+  |  |  |
|  |  (antenna)     |    |  |Protocol  |  |  Clinical UI  |  |  |  |
|  +----------------+    |  |Handler   |  |  (stim params,|  |  |  |
|                        |  +----------+  |   signal viz) |  |  |  |
|                        |  +----------+  +---------------+  |  |  |
|                        |  |Security  |                     |  |  |
|                        |  |Module    |                     |  |  |
|                        |  +----------+                     |  |  |
|                        +--------------+--------------------+  |  |
|                                       |                       |  |
|                                       v                       |  |
|                        +------------------------------+       |  |
|                        |     Hospital Network          |       |  |
|                        |  (EHR integration, cloud      |       |  |
|                        |   backup, remote monitoring)   |       |  |
|                        +------------------------------+       |  |
+============================================================+====+
```

### 9.2 Data Flow with Security Annotations

1. **Neural signal acquisition** (Lead to AFE to ADC): Analog domain. No cryptographic protection possible. Integrity depends on physical security of the implant and electromagnetic compatibility. An attacker with physical access to the patient can inject EMI directly. The only defense is the patient's own body tissue (which provides some natural shielding) and the device's EMI filtering.

2. **Digital signal processing** (Microcontroller): Digital domain inside the implant. Firmware integrity depends on secure boot and firmware update mechanism. If secure boot is properly implemented, the firmware running on the microcontroller is guaranteed to be manufacturer-authorized. If secure boot is absent or broken, an attacker can run arbitrary firmware.

3. **Telemetry transmission** (RF Antenna to Wireless Link to Programmer Wand): The primary attack surface. Security properties depend on protocol implementation: authentication (who can talk to the implant), encryption (who can read the data), integrity protection (has the data been modified), replay protection (is this a fresh message or a recorded one). Each of these must be independently evaluated.

4. **Clinical processing** (Programmer Tablet): Software application. Security depends on application security (input validation, secure coding), OS security (OS hardening, malware resistance), and network security (TLS for data transmission). This is a standard software security domain with well-understood assessment methodologies.

5. **Data storage and transmission** (Hospital Network to Cloud): Standard IT security domain. Security depends on TLS for transit, encryption at rest, access controls, audit logging. The neural data's unique sensitivity means that standard medical data protection (HIPAA, GDPR) applies but may be insufficient given the data's biometric and cognitive content.

## 10. Internal Components

### 10.1 Analog Front-End ASIC

The AFE is the most silicon-intensive component in the IPG. It typically includes:

- **Low-noise amplifier (LNA):** Amplifies neural signals with minimal added noise. Typical input-referred noise: 1-5 uV RMS for EEG-range signals, 0.5-2 uV RMS for spike-range signals. The noise performance directly determines signal quality and therefore the device's clinical efficacy.

- **Programmable gain amplifier (PGA):** Allows adjustment of amplification to match different electrode impedances and signal levels. In implantable devices, gain is typically set at implantation and rarely changed.

- **Anti-aliasing filter:** Analog low-pass filter before the ADC to prevent aliasing. Cutoff frequency is set based on the signal modality (e.g., 500 Hz for EEG, 10 kHz for spike recording).

Security relevance: The AFE is not programmable in most implantable devices, which means it is not directly attackable via the wireless interface. However, EMI injection at the electrode terminals can inject signals before the AFE, bypassing any digital security measures. This is an important limitation of purely digital security approaches — the analog domain has no cryptographic protection.

### 10.2 Microcontroller

The microcontroller (MCU) is the brain of the IPG. Typical implementations:

- **Core:** ARM Cortex-M0/M3/M4 in most commercial devices. Some use custom cores for specific power or performance requirements. The ARM architecture is dominant because of the mature toolchain, wide availability of IP blocks, and well-understood security features (MPU, TrustZone in some implementations).

- **Memory:** 256 KB to 2 MB flash, 64 KB to 512 KB SRAM typical. Memory is a scarce resource in implantable devices because every byte of memory consumes power.

- **Peripherals:** ADC interface, SPI/I2C for RF module communication, GPIO for electrode switching, timer for stimulation pulse generation.

Security features to evaluate:
- **Secure boot:** Does the MCU verify firmware integrity before execution? Is the verification based on RSA/ECDSA signatures or simpler (and breakable) checksums?
- **Memory Protection Unit (MPU):** Is firmware memory separated from data memory? Can a buffer overflow in the telemetry handler overwrite stimulation control code?
- **Debug interface:** Is JTAG/SWD disabled in production? Are there undocumented debug modes?
- **Watchdog timer:** Is there an independent hardware watchdog that can detect firmware hangs and switch to a safe state?

### 10.3 RF Telemetry Module

The RF module implements the wireless protocol. In implantable devices, the radio must operate within specific regulatory bands:

- **MICS band (402-405 MHz):** Medical Implant Communication Service. Licensed spectrum specifically for medical implants. Low power, low bandwidth (up to 250 kbps), short range (1-2 m). Used by most implantable neural devices.

- **ISM band (2.4 GHz):** Industrial, Scientific, Medical. Unlicensed spectrum. Higher bandwidth but higher power consumption and more interference. Used by some consumer neurotechnology devices and some research implants.

- **BLE (2.4 GHz):** Bluetooth Low Energy. Standardized protocol with wide support. Used by consumer BCIs and increasingly by medical devices. The standardization means well-understood security (or lack thereof) but also well-understood attack tools.

Security evaluation of the RF module must examine:
- **Protocol implementation correctness:** Are there buffer overflows, integer overflows, or state machine bugs in the protocol handler?
- **Cryptographic implementation:** Are there timing side channels, padding oracle vulnerabilities, or weak random number generation?
- **Physical layer:** Can the modulation be spoofed? Can a software-defined radio impersonate a legitimate programmer?

### 10.4 Safety Monitor

The safety monitor is the last line of defense against dangerous stimulation. It is typically implemented as:

- **Hardware safety circuit:** Independent of the microcontroller. Monitors stimulation voltage, current, charge per phase, and duty cycle. Shuts down stimulation if any parameter exceeds hard-coded limits. Cannot be bypassed by firmware attacks.

- **Firmware safety monitor:** Software that runs independently of the main firmware (on a separate core or at a higher privilege level). Verifies that stimulation commands are within therapist-programmed limits before execution.

Security relevance: The safety monitor provides defense-in-depth. Even if an attacker gains full control of the main firmware, the hardware safety circuit prevents stimulation beyond absolute limits. However, the safety monitor cannot distinguish between a legitimate in-range parameter and an adversarial in-range parameter. An attacker who knows the therapeutic parameter range can set any value within that range without triggering the safety monitor.

## 11. Communication Flow

### 11.1 Typical Telemetry Session

A typical telemetry session between a clinician programmer and an implantable neural device follows this sequence:

**Phase 1: Session Initiation**
- The programmer wand broadcasts an interrogation message on the MICS band containing a device type identifier.
- The IPG, which is in a low-power listening mode, wakes up and responds with its device identifier, model number, firmware version, and current therapy status.
- The programmer displays the patient's programmed parameters and current device status to the clinician.

Security concerns: The interrogation message is typically unauthenticated and unencrypted. Any device that broadcasts the correct interrogation format will receive a response. This is a passive information disclosure vulnerability — an attacker with a MICS-band receiver can detect the presence of an implant and learn its type and firmware version.

**Phase 2: Authentication**
- The programmer sends a challenge (random nonce) to the IPG.
- The IPG computes a message authentication code (MAC) over the challenge using a shared secret key and returns the MAC.
- The programmer verifies the MAC and, if correct, derives a session key for encrypted communication.

Security concerns: The strength of the authentication depends on the key length, the MAC algorithm, the quality of the random number generator, and whether the shared secret is properly protected. In legacy devices, authentication may be absent entirely.

**Phase 3: Parameter Read/Write**
- The programmer reads current stimulation parameters and neural signal data (in sensing-capable devices).
- The clinician reviews the data and may adjust stimulation parameters.
- New parameters are transmitted to the IPG, which verifies they are within safety limits before applying them.

Security concerns: Parameter modification is the highest-impact attack. An attacker who can inject parameter modification commands can change therapy delivery. Replay attacks are a concern if the protocol lacks replay protection (nonces or timestamps).

**Phase 4: Session Termination**
- The programmer sends a session end command.
- The IPG returns to low-power listening mode.

Security concerns: Premature session termination could leave the device in an inconsistent state. Session hijacking (taking over an active session) is possible if the session identifier is predictable.

### 11.2 Data Frame Structure

A typical proprietary telemetry frame structure (generalized from multiple devices):

```
+--------+--------+----------+--------+---------+--------+
| Preamble| Header | Payload  | CRC/MAC| Payload | Footer |
| (sync) | (type, | (data)   |        | Encrypt |        |
|        | len,   |          |        |         |        |
|        | seq)   |          |        |         |        |
+--------+--------+----------+--------+---------+--------+
```

Security evaluation must determine:
- Is the preamble predictable? (Used for synchronization — predictable is normal but means any receiver can detect frame starts)
- Is the header authenticated? (If not, an attacker can modify frame type or length fields)
- Is the payload encrypted? (If not, all data is readable by any compatible receiver)
- Is the CRC/MAC applied before or after encryption? (Encrypt-then-MAC is correct; MAC-then-encrypt and encrypt-and-MAC have known weaknesses)
- Is there replay protection? (Sequence numbers that are checked by the receiver)

## 12. Trust Boundaries

Trust boundaries in a neurotechnology system are the points where data crosses from one security domain to another:

```
+------------------+     +------------------+     +------------------+
|   Implant Body   |     |   Wireless Link  |     |  Clinician Side  |
|   (Trusted)      |---->|  (Untrusted)      |---->|  (Trusted)       |
|                  |     |                  |     |                  |
|  - IPG firmware  |     |  - RF spectrum   |     |  - Programmer    |
|  - Neural data   |     |  - Protocol      |     |    application   |
|  - Safety limits |     |    messages      |     |  - Hospital      |
|                  |     |  - Potential     |     |    network       |
|                  |     |    attacker      |     |  - Cloud         |
+------------------+     +------------------+     +------------------+

+------------------+     +------------------+
|  Hospital        |---->|   Cloud / EHR    |
|  Network         |     |   (Partially     |
|  (Semi-trusted)  |     |    trusted)      |
+------------------+     +------------------+
```

Key trust boundary crossings:

1. **Implant to Wireless (TB-1):** Data leaves the physically protected implant body. This is the highest-risk trust boundary. The implant's internal state is relatively secure (physical access required), but once data is transmitted wirelessly, it is exposed to anyone with a compatible receiver.

2. **Wireless to Programmer (TB-2):** Data arrives at the external programmer. The programmer must verify data integrity and authenticity. The programmer is typically a trusted device, but if it is compromised (malware, stolen), it becomes an attack vector.

3. **Programmer to Hospital Network (TB-3):** Data moves from a medical device to standard IT infrastructure. This boundary involves protocol translation (proprietary telemetry to TCP/IP) and introduces all standard network security concerns.

4. **Hospital Network to Cloud (TB-4):** Data moves from a controlled hospital environment to a shared cloud infrastructure. Different trust model (cloud provider is a third party) and raises data residency and sovereignty concerns.

5. **Clinician to Programmer (TB-5):** The human-machine interface. Social engineering, credential theft, and insider threats are relevant here.
