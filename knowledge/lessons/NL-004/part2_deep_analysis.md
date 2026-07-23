# NL-004: Wireless Protocol Security for Neurostimulators (Part 2)

## 9. Protocol Reverse Engineering

### 9.1 Why Reverse Engineer a Protocol

VIREON must validate protocol security for devices where the protocol specification is proprietary. Unlike BLE (publicly documented), most MICS-band neurostimulator protocols are proprietary — the only way to understand the protocol is to observe it in action.

Protocol reverse engineering (PRE) is the process of deducing a protocol's specification from observed communication. It involves capturing packet traces, identifying patterns, and reconstructing the protocol's state machine, packet format, and security mechanisms.

### 9.2 PRE Methodology

**Step 1: Passive Observation**
Capture wireless traffic between a programmer and an implant (or, for VIREON's simulation, between the Lab 001 simulator components). Record: packet timing, packet sizes, and raw bytes. Do not transmit — only listen.

- Identify the packet boundaries (preamble + sync patterns)
- Measure inter-packet timing (reveals timeout values, retry behavior)
- Identify repeating patterns (keep-alive messages, status queries)
- Note packet size distribution (commands are small, telemetry may be larger)

**Step 2: Active Probing**
Transmit crafted packets to the implant/simulator and observe the response:

- Send valid packets with modified fields (one field at a time) to determine which fields are validated
- Send packets of various sizes to determine the acceptable range
- Send rapid sequences to determine rate limits and timeout values
- Send valid packets with invalid authentication to determine the error response

**Step 3: Security Mechanism Identification**
- Identify whether packets are encrypted (entropy analysis of payload)
- Identify the encryption algorithm (by comparing observed ciphertext with known encryption patterns)
- Identify the authentication mechanism (by observing which field changes cause rejection)
- Identify the session establishment process (by observing the initial handshake)

### 9.3 VIREON Protocol Fingerprinting

VIREON should build a database of known protocol fingerprints for commercially available neurostimulators:

| Device | MICS Freq | Modulation | Data Rate | Encryption | Notes |
|---|---|---|---|---|---|
| Medtronic Percept PC | 403 MHz | GFSK | 400 kbps | AES-128 | Proprietary protocol |
| Abbott Infinity | 402-405 MHz | GFSK | 250 kbps | AES-128-CCM | Merlin protocol |
| Boston Scientific Vercise | 402 MHz | GFSK | 500 kbps | AES-128 | Proprietary |
| (Generic) | Various | GFSK | 250-800 kbps | Varies | Unknown protocols |

This fingerprint database enables VIREON to identify a device's protocol from a short packet capture, which then selects the appropriate security test suite.

## 10. Protocol Simulation for VIREON

### 10.1 Simulated MICS Protocol Design

For VIREON's digital twin, we implement a simplified but security-complete MICS protocol:

**Physical layer:** GFSK modulation at 400 kbps, centered at 403.65 MHz (mid-band).

**MAC layer:** CSMA/CA with LBT. Frame format:
```
| Preamble (2B) | Sync (1B: 0xAA) | Length (1B) | Payload (N B) | CRC-16 (2B) |
```

**Security layer:** AES-128-CCM with 12-byte nonce, 8-byte authentication tag. The nonce is composed of: device address (2B) + session counter (4B) + packet counter (4B) + padding (2B).

**Transport layer:** Reliable delivery with ACK/retry. Max 3 retries per packet. Sliding window of 8 packets.

**Application layer:** Command/response protocol with 16 command types.

### 10.2 Protocol State Machine

The simulated protocol implements the state machine from Section 6.1:
- SLEEP → IDLE: on RF wake signal (external magnetic switch or RF carrier detect)
- IDLE → AUTH: on valid session request
- AUTH → ACTIVE: on successful authentication
- ACTIVE → IDLE: on session termination or timeout
- Any → SLEEP: on inactivity timeout (configurable, default 30 seconds)

### 10.3 Security Instrumentation

The simulated protocol logs all security-relevant events:
- Every packet received (with source, size, RSSI)
- Authentication success/failure (with reason)
- Replay detection (sequence number check result)
- Session establishment (with key derivation details)
- Cryptographic operations (algorithm, key ID, nonce, duration)

These logs enable VIREON to reconstruct the protocol's security behavior after a test run.

## 11. Application Protocol Analysis

### 11.1 Command Types and Security

A typical neurostimulator application protocol supports the following command types:

| CMD ID | Name | Direction | Security Class | Impact if Compromised |
|---|---|---|---|---|
| 0x01 | GET_STATUS | P → I | Low | Information disclosure |
| 0x02 | GET_IMPEDANCE | P → I | Low | Information disclosure |
| 0x03 | GET_DIAGNOSTICS | P → I | Medium | Device behavior info |
| 0x04 | SET_AMPLITUDE | P → I | Critical | Unsafe stimulation |
| 0x05 | SET_FREQUENCY | P → I | Critical | Unsafe stimulation |
| 0x06 | SET_PULSE_WIDTH | P → I | Critical | Unsafe stimulation |
| 0x07 | SET_ELECTRODE | P → I | Critical | Wrong stimulation site |
| 0x08 | START_THERAPY | P → I | High | Unwanted stimulation |
| 0x09 | STOP_THERAPY | P → I | High | Therapy interruption |
| 0x0A | SET_CL_PARAMS | P → I | Critical | Controller manipulation |
| 0x0B | GET_NEURAL_DATA | P → I | High | Neural data exfiltration |
| 0x0C | OTA_UPDATE | P → I | Critical | Firmware compromise |
| 0x0D | PAIRING_REQUEST | P → I | High | New pairing session |
| 0x0E | SESSION_END | Bidirectional | Low | Session termination |
| 0x0F | EMERGENCY_STOP | P → I | Critical | Immediate therapy halt |

**Security design principle:** Each command type should have a security class that determines the authorization level required to execute it. Critical commands (0x04-0x07, 0x0A, 0x0C) should require the highest authorization level (clinic programmer with valid credentials). Low commands (0x01, 0x02, 0x0E) can be executed by home monitoring equipment.

### 11.2 Command Authorization Levels

| Level | Name | Required Credential | Commands Allowed |
|---|---|---|---|
| 0 | Emergency | Physical proximity (magnetic switch) | 0x0F only |
| 1 | Home Monitoring | Patient smartphone (BLE pairing) | 0x01-0x03, 0x0E |
| 2 | Clinical Programming | Clinic programmer (MICS + clinician auth) | 0x01-0x0F |
| 3 | Firmware Update | Manufacturer (signed firmware) | 0x0C only |

**Security implication:** The authorization level must be verified per-command, not per-session. A home monitoring session (level 1) must not be able to execute clinical commands (level 2), even if the session is authenticated. The Medtronic insulin pump vulnerability (NL-003 Section 16.2) demonstrated the consequences of per-session authorization.

### 11.3 Response Protocol

The implant responds to each command with a response packet:

```
| Response Code (1B) | Payload (variable) |

Response codes:
  0x00 = SUCCESS
  0x01 = INVALID_COMMAND
  0x02 = UNAUTHORIZED
  0x03 = PARAMETER_OUT_OF_RANGE
  0x04 = DEVICE_BUSY
  0x05 = SAFETY_VIOLATION
  0x06 = CRYPTO_ERROR
  0x07 = UNKNOWN
```

**Security implication:** The response code reveals information about the implant's state. An attacker who sends a series of commands and observes the responses can map the implant's behavior: which commands are supported, which parameter values are accepted, and what the current state is. This information leakage is inherent in any request-response protocol and cannot be fully eliminated. The mitigation is to limit the rate of command attempts (rate limiting) and to return generic error codes for security failures (e.g., always return 0x07 for authentication failures, not 0x06).

## 12. Known Protocol Vulnerabilities

### 12.1 Abbott/St. Jude Merlin@home (2016-2017)

**Vulnerability:** The Merlin@home transmitter communicated with implantable cardiac devices using an unencrypted RF channel in the MICS band. While this is a cardiac device, the protocol architecture is identical to what neurostimulators use.

**Protocol detail:** The transmitter used a custom protocol that included no encryption for the home monitoring channel. The clinical programmer channel was encrypted, but the home monitoring channel (used for daily data uploads) transmitted therapy parameters and diagnostic data in cleartext.

**Attack impact:** An attacker within 10 meters could read therapy parameters, modify device settings, and drain the battery. The lack of encryption meant that standard SDR equipment could capture and analyze all traffic.

**Root cause analysis:** The encryption was omitted from the home monitoring channel to reduce power consumption and complexity. The risk assessment incorrectly concluded that the home monitoring channel did not carry security-sensitive data (it did: therapy parameters and device identifiers).

**VIREON lesson:** Every communication channel, regardless of its intended use, must be encrypted if it carries any information that could be used to attack the device or the patient. The cost of AES-128-CCM (0.05 uJ/block) is negligible compared to the device's total power budget (5-20 mW).

### 12.2 Medtronic Conexus Telemetry Protocol

**Vulnerability:** The Conexus protocol (used in Medtronic's implantable devices, including some neurostimulators) was found to use a weak pairing mechanism and insufficient replay protection in earlier versions.

**Protocol detail:** The protocol used a short device identifier (serial number) as a pre-shared key for session establishment. The serial number is printed on the device packaging and can be obtained by anyone with access to the clinic's inventory or the patient's records.

**Attack impact:** Knowledge of the serial number enables an attacker to establish a session with the device and send commands.

**Mitigation:** Newer versions use longer, cryptographically random pairing keys and add per-packet authentication.

### 12.3 Generic Protocol Vulnerabilities in Implants

1. **No encryption:** Some older devices transmit all data in cleartext. This is the most basic vulnerability but is still found in devices manufactured before 2015.

2. **Static encryption key:** Some devices use the same encryption key for all sessions and all devices (a global key). Extracting the key from one device compromises all devices.

3. **No replay protection:** Devices that accept any validly-formatted packet without sequence number checking are vulnerable to replay attacks.

4. **Weak random number generation:** Devices that use a counter or LFSR as a "random" number generator produce predictable nonces, enabling session key prediction.

5. **No session timeout:** Devices that maintain sessions indefinitely (no inactivity timeout) are vulnerable to session hijacking if the session key is compromised.

## 13. Protocol Security Validation

### 13.1 VIREON Protocol Validation Levels

**Level 1 — Specification Review:** Review the protocol specification (or reverse-engineered specification) for known vulnerability patterns. Check for: missing encryption, weak key management, insufficient replay protection, inadequate authorization.

**Level 2 — Packet Fuzzing:** Send malformed packets to the protocol implementation and observe the response. Measure crash rate, authentication failure rate, and response code distribution.

**Level 3 — Attack Simulation:** Execute specific attack scenarios (replay, injection, desynchronization, battery drain) against the protocol implementation and measure the detection and mitigation effectiveness.

**Level 4 — Cryptographic Analysis:** Verify the correctness of the cryptographic implementation: nonce uniqueness, constant-time comparison, proper AEAD usage, key derivation randomness.

### 13.2 Protocol Security Properties to Validate

| Property | Description | Validation Method |
|---|---|---|
| Confidentiality | Payload is encrypted | Capture encrypted traffic, verify no plaintext leakage |
| Integrity | Payload + header authenticated | Modify authenticated packets, verify rejection |
| Authenticity | Only authorized parties can communicate | Attempt session establishment without valid credentials |
| Replay resistance | Duplicate packets are rejected | Replay recorded packets from same/different sessions |
| Forward secrecy | Compromising long-term key doesn't reveal past sessions | Record sessions, compromise key, attempt decryption |
| Authorization | Per-command authorization is enforced | Execute commands with insufficient authorization |
| Availability | Protocol resists DoS | Flood with packets, measure response degradation |
| Battery resilience | Protocol resists battery drain | Measure energy consumed during attack scenarios |

## 14. Benchmarking Methodology

### 14.1 Protocol Security Benchmarks

| ID | Benchmark | Category | Difficulty | Description |
|---|---|---|---|---|
| WP-001 | Cleartext eavesdropping | Confidentiality | Easy | Capture traffic, verify no plaintext |
| WP-002 | Replay (cross-session) | Replay | Easy | Replay packets from previous session |
| WP-003 | Replay (within-session) | Replay | Medium | Replay packets from current session |
| WP-004 | Packet injection | Integrity | Medium | Inject crafted packets with valid auth |
| WP-005 | Desynchronization | Availability | Medium | Send packets with future sequence numbers |
| WP-006 | Command flooding | Availability | Easy | Send 1000 packets/second for 60 seconds |
| WP-007 | Battery drain measurement | Battery | Medium | Measure energy during attack vs. normal |
| WP-008 | Authorization bypass | Authorization | Hard | Execute critical commands with level 1 auth |

### 14.2 Benchmark Scoring

- **WP-001:** Score = 10 if no plaintext detected, 0 if plaintext found.
- **WP-002/003:** Score = 10 * (replayed_packets_rejected / total_replayed).
- **WP-004:** Score = 10 * (injected_packets_rejected / total_injected).
- **WP-005:** Score = 10 if legitimate session recovers within 5 seconds, 0 if not.
- **WP-006:** Score = 10 * (legitimate_commands_processed / total_legitimate_during_attack).
- **WP-007:** Score = 10 * (1 - attack_energy / normal_energy * attack_duration / normal_duration).
- **WP-008:** Score = 10 * (unauthorized_commands_rejected / total_unauthorized).

## 15. Wireless Channel Security Properties

### 15.1 Channel Characteristics as Security Barriers

| Characteristic | Security Benefit | Security Limitation |
|---|---|---|
| Low transmit power (25 uW) | Limits eavesdropping range | Sensitive receiver extends range |
| Tissue attenuation (20-40 dB) | Requires close proximity | Directional antenna compensates |
| Narrow bandwidth (3 MHz) | Limits data rate for attacker | Adequate for command injection |
| LBT (listen-before-talk) | Prevents accidental collisions | Attacker can intentionally jam |
| Body shielding | Reduces external interference | Patient-specific, variable |

### 15.2 Eavesdropping Range Estimation

For a typical MICS implant communication:

| Receiver | Antenna Gain | Sensitivity | Max Eavesdrop Range |
|---|---|---|---|
| Consumer SDR | 0 dBi | -100 dBm | ~2 meters |
| SDR + LNA | 3 dBi | -120 dBm | ~20 meters |
| SDR + directional + LNA | 10 dBi | -130 dBm | ~100 meters |
| Research-grade receiver | 15 dBi | -140 dBm | ~500 meters |

**Security implication:** While the "casual eavesdropper" with a consumer SDR is limited to ~2 meters, a motivated attacker with good equipment can eavesdrop from 100+ meters. Protocol security must not rely on the physical layer for confidentiality — the cryptographic layer must provide confidentiality regardless of the eavesdropper's range.

### 15.3 Jamming and Anti-Jamming

**Jamming attack:** Transmit noise or a continuous carrier on the MICS channel, preventing the implant from communicating with the legitimate programmer.

**Anti-jamming techniques:**
1. **Frequency hopping:** Spread the communication across multiple MICS channels (e.g., hop every 100 ms between 10 channels). The attacker must jam all channels simultaneously, requiring 10x the power.
2. **Adaptive frequency selection:** The implant monitors channel quality and switches to the least-interfered channel. Requires the attacker to track the channel switches.
3. **Temporal diversity:** If communication is intermittent (e.g., daily data upload), the attacker must maintain jamming continuously, draining the attacker's equipment battery.

**VIREON validation:** Test the protocol's behavior under jamming conditions. The device should: detect the jamming condition, log the event, and gracefully terminate the session (not hang or crash).

## 16. Dual-Channel Coordination

### 16.1 MICS + BLE Coordination Architecture

```
                    ┌─────────────────┐
                    │  Cloud Platform  │
                    └────────┬────────┘
                             │ (HTTPS)
                    ┌────────┴────────┐
                    │  Smartphone App  │
                    │  (BLE channel)   │
                    └────────┬────────┘
                             │ BLE
                    ┌────────┴────────┐
                    │  Neurostimulator │
                    │  (both channels) │
                    └────────┬────────┘
                             │ MICS
                    ┌────────┴────────┐
                    │  Clinic Programmer│
                    └─────────────────┘
```

### 16.2 Cross-Channel Security Policies

| Policy | Description | Rationale |
|---|---|---|
| MICS priority | MICS commands override BLE commands | Clinical programming takes precedence over home monitoring |
| Shared session lock | Only one session active at a time | Prevents conflicting commands from two sources |
| Independent keys | MICS and BLE use different session keys | Compromising one channel doesn't compromise the other |
| Unified audit log | All channel events logged to same audit trail | Enables cross-channel attack detection |
| BLE rate limit | BLE commands limited to 1/second | Prevents rapid BLE command flooding |
| MICS auth required | All MICS commands require full clinical auth | MICS is the high-privilege channel |

**VIREON validation:** Test cross-channel attacks: send conflicting commands simultaneously on both channels, verify that the priority policy is correctly enforced, and verify that the shared session lock prevents concurrent sessions.

### 16.3 Cloud Communication Security

The smartphone app communicates with a cloud platform via HTTPS (TLS 1.3). The cloud stores: therapy parameters, diagnostic data, device status, and firmware version.

**Security implications:**
- The cloud is a high-value target — it contains data from ALL patients, not just one.
- Cloud credentials (API keys, OAuth tokens) on the smartphone must be stored securely.
- The cloud must implement per-patient access control — a clinician should only access their own patients' data.
- Cloud-stored neural data (if any) must be encrypted at rest with per-patient keys.

While cloud security is outside the primary scope of this module (it's standard web security), the wireless protocol's interaction with the cloud creates a chain: the protocol secures the implant-to-smartphone link, TLS secures the smartphone-to-cloud link, and the cloud's access control secures the data. A vulnerability in any link breaks the chain.