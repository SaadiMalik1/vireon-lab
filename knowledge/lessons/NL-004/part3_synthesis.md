# NL-004: Wireless Protocol Security for Neurostimulators (Part 3)

## 17. STRIDE Threat Model for Wireless Protocols

| Threat | Protocol-Specific Instance | Impact | Existing Mitigation | Gap |
|---|---|---|---|---|
| **Spoofing** | Impersonate clinic programmer | Unauthorized command execution | Session authentication (challenge-response) | Weak pairing keys, session hijacking |
| **Tampering** | Modify encrypted packet | Command manipulation | AES-CCM authentication tag | Header not covered by auth tag |
| **Repudiation** | Deny sending a command | Accountability failure | Packet logging with sequence numbers | Logs stored only in implant (limited storage) |
| **Information Disclosure** | Eavesdrop on MICS channel | Neural data/parameter exposure | AES-CCM encryption | Legacy devices without encryption |
| **Denial of Service** | RF jamming or packet flooding | Therapy interruption | Adaptive frequency selection | Limited by MICS narrow bandwidth |
| **Elevation of Privilege** | Use home monitoring to send clinical commands | Safety-critical command execution | Per-command authorization | Authorization often per-session, not per-command |

## 18. Failure Modes in Protocol Security

### 18.1 Cryptographic Failure Modes

| Failure Mode | Cause | Effect | Detection | Mitigation |
|---|---|---|---|---|
| Nonce reuse | Counter reset after reboot | Keystream reuse → plaintext recovery | Per-packet nonce audit | Nonce includes boot counter |
| Key exhaustion | Too many sessions with derived keys | Degraded key material | Session count monitoring | Periodic re-pairing |
| Timing side-channel | Variable crypto execution time | Key bit leakage | Timing analysis | Constant-time implementation |
| Random number failure | Low-entropy RNG | Predictable nonces | Statistical tests on nonces | Hardware TRNG with health tests |

### 18.2 Protocol Failure Modes

| Failure Mode | Cause | Effect | Detection | Mitigation |
|---|---|---|---|---|
| Session desync | Seq number mismatch | Legitimate packets rejected | Retry counter monitoring | Resync protocol |
| Reassembly overflow | Malicious fragment size | Memory corruption | Fragment size validation | Strict total length check |
| State machine deadlock | Bug in state transitions | Device stuck in one state | Inactivity timeout | Timeout on every state |
| ACK storm | Retransmission loop | Bandwidth saturation | Duplicate ACK detection | Exponential backoff |

## 19. Security Implications Summary

### 19.1 Defense-in-Depth for Protocol Security

VIREON's protocol security approach layers multiple defenses:

1. **Physical layer:** Low transmit power, tissue attenuation, LBT (not security mechanisms, but provide range limitation)
2. **MAC layer:** CRC for error detection, device addressing for targeted communication
3. **Security layer:** AES-CCM for confidentiality and integrity, ECDSA for firmware signing
4. **Transport layer:** Sequence numbers for replay protection, ACK/retry for reliability
5. **Application layer:** Per-command authorization, parameter validation, safety limits
6. **Firmware layer (NL-003):** Input validation, buffer overflow protection, safety monitor
7. **Behavioral layer:** Anomaly detection on command patterns, rate limiting, battery monitoring

Each layer catches attacks that the previous layer misses. The critical insight is that no single layer is sufficient — and the composition of layers must be validated, not just the individual layers.

## 20. Known Attacks in Detail

### 20.1 Halperin et al. Pacemaker Attack (2008)

**Method:** Used an SDR to capture and analyze the communication between a pacemaker programmer and an implant. Identified the modulation scheme, packet format, and discovered that the communication was unencrypted.

**Attack chain:** (1) Capture traffic → (2) Identify packet format → (3) Extract device identifiers → (4) Craft command packets → (5) Transmit commands to modify therapy.

**Relevance to neurostimulators:** The attack methodology is directly applicable. The specific commands differ (cardiac pacing vs. neural stimulation), but the protocol-level attack steps are identical. Any neurostimulator with similar protocol weaknesses (unencrypted, no replay protection) is equally vulnerable.

### 20.2 Relay Attack on Implant Communication

**Method:** Two attackers collaborate: one near the patient (relaying to the implant) and one near the programmer (relaying from the programmer). The patient and programmer are at different locations, but the relay makes them appear adjacent.

**Attack chain:** (1) Attacker A sends session request to implant → (2) Implant sends challenge → (3) Attacker A relays challenge to Attacker B → (4) Attacker B sends challenge to programmer → (5) Programmer responds → (6) Attacker B relays response to Attacker A → (7) Attacker A sends response to implant → (8) Session established with attacker in the middle.

**Detection:** The relay introduces latency (typically 10-100 ms depending on the relay link). If the protocol has a tight timeout on the challenge-response (e.g., 50 ms), the relay may fail. However, most neurostimulator protocols have generous timeouts (100-500 ms) to accommodate slow cryptographic operations, making relay attacks feasible.

**Mitigation:** Distance bounding protocols measure the round-trip time of the challenge-response and reject responses that take too long (indicating a relay). However, distance bounding is challenging over the MICS channel due to variable tissue propagation delays.

## 21. Common Misconceptions

**Misconception 1: "The MICS band is secure because it requires a medical device license to transmit."**
Reality: SDRs can transmit on any frequency. A license is required for legal operation, not for technical capability. An attacker does not need a license.

**Misconception 2: "The tissue attenuation means the attacker must be touching the patient."**
Reality: With a directional antenna and LNA, an attacker can be 10-100+ meters away. Tissue attenuation is 20-40 dB, not 100 dB.

**Misconception 3: "Encryption is all you need for protocol security."**
Reality: Encryption provides confidentiality and (with AEAD) integrity. It does NOT provide replay protection, authorization, availability, or resistance to protocol-level attacks like desynchronization or battery drain.

**Misconception 4: "BLE is secure because it's a standard with extensive analysis."**
Reality: BLE has known vulnerabilities (KNOB, BLESA, BLUR). The standard's security is good but not perfect, and the implementation may deviate from the standard.

**Misconception 5: "The protocol is proprietary, so attackers can't figure it out."**
Reality: Protocol reverse engineering is a well-understood discipline. Proprietary protocols have been reverse-engineered for pacemakers, insulin pumps, and neurostimulators. Obscurity is not security.

## 22. Engineering Trade-offs

### 22.1 Security Overhead vs. Bandwidth

AES-CCM adds 8-16 bytes of authentication tag per packet and requires a 12-byte nonce. For a typical 32-byte command packet, the security overhead is 20-28 bytes (62-87% overhead). This significantly reduces the effective data rate. Reducing the tag length to 4 bytes reduces overhead but increases the forgery probability.

### 22.2 Security Overhead vs. Latency

Each cryptographic operation (encrypt + MAC) takes 5-20 us on a Cortex-M4. For a protocol that processes one packet per 4 ms, this is 0.25-1.25% overhead — negligible. However, session establishment requires ECDSA verification (20-80 ms), which is a noticeable delay for the user (clinician must wait for the handshake to complete before programming).

### 22.3 Security Strength vs. Battery Life

Every transmitted bit consumes battery energy. Security overhead (tags, nonces, encrypted headers) increases the number of bits per command, increasing energy per command. For a device with a 10-year battery life, the security overhead might reduce battery life by 5-15%. This is an acceptable trade-off — the alternative (no security) is not acceptable.

## 23. Future Directions

**Ultra-wideband (UWB) for implants:** UWB provides precise ranging (cm-level) that enables distance bounding protocols. If the protocol measures the round-trip distance and rejects sessions where the programmer is more than 2 meters away, relay attacks become infeasible.

**Post-quantum cryptography:** Lattice-based KEMs (e.g., Kyber) are being considered for future implant protocols to provide quantum resistance. The computational cost is 5-10x higher than ECDH, but may become feasible as hardware accelerators are developed.

**Cognitive radio:** Implants that can dynamically switch between MICS, BLE, and other bands based on interference conditions. This provides availability under jamming but increases the protocol's complexity and attack surface.

**Physical layer security:** Using the unique characteristics of the tissue channel (channel state information) as an additional authentication factor. The idea is that the channel response between the implant and the legitimate programmer is unique and difficult to spoof.

## 24. Relation to VIREON Architecture

### 24.1 VIREON Components Produced by NL-004

- **`ProtocolAnalyzer` provider:** Analyzes packet captures for security properties.
- **`PacketFuzzer` provider:** Generates malformed packets for fuzzing.
- **`ReplayDetector` provider:** Detects replay attacks in packet streams.
- **Benchmark definitions:** WP-001 through WP-008 standardized protocol security test scenarios.
- **`WirelessChannel` model:** Simulated MICS channel model for digital twin integration.

### 24.2 Digital Twin Integration

Lab 001's protocol simulator provides the wireless channel model for VIREON's digital twin. It models: packet transmission, channel noise, packet loss, and timing — enabling protocol security testing without physical hardware.

## 25. Exercises

### Exercise 1: Protocol Fingerprinting (2 hours)
Using Lab 001's simulator, capture a session and identify the protocol parameters: modulation, data rate, packet format, encryption algorithm, and session establishment process.

### Exercise 2: Replay Attack Simulation (2 hours)
Using Lab 002, execute replay attacks (WP-002, WP-003) and measure the detection rate. Analyze which replay variants are detected and which are not.

### Exercise 3: Protocol Security Audit (3 hours)
Given a protocol specification (provided in the exercise), perform a security audit identifying all vulnerability classes from Section 7.1. Produce a prioritized vulnerability list with recommended mitigations.

### Exercise 4: Battery Drain Measurement (2 hours)
Using Lab 002, simulate battery drain attacks (WP-007) and measure the energy consumed during different attack scenarios. Compare to normal operation energy.

## 26. Concept Map

```
Wireless Protocol Security
├── Physical Layer (MICS/BLE)
│   ├── MICS band (402-405 MHz)
│   ├── BLE (2.4 GHz)
│   ├── Tissue channel model
│   └── Eavesdropping range analysis
├── Protocol Stack
│   ├── Packet structure (preamble, header, payload, auth, CRC)
│   ├── Session establishment (pairing, challenge-response, KDF)
│   ├── Sequence number management (replay window)
│   ├── Fragmentation/reassembly
│   └── State machine (SLEEP, IDLE, AUTH, ACTIVE)
├── Cryptographic Mechanisms
│   ├── AES-CCM (confidentiality + integrity)
│   ├── ECDSA (firmware signing, optional session auth)
│   ├── HKDF (key derivation)
│   └── Nonce management
├── Attack Classes
│   ├── Eavesdropping
│   ├── Packet injection
│   ├── Replay (cross-session, within-session)
│   ├── Desynchronization
│   ├── Battery drain
│   ├── Relay attack
│   └── Jamming
├── Defenses
│   ├── Authenticated encryption
│   ├── Per-command authorization
│   ├── Sequence number windows
│   ├── Rate limiting
│   └── Inactivity timeout
└── VIREON Integration
    ├── Protocol Analyzer provider
    ├── WP-001 through WP-008 benchmarks
    └── Wireless channel digital twin model
```

## 27. Glossary

- **AEAD:** Authenticated Encryption with Associated Data — encryption that also provides integrity.
- **BLE:** Bluetooth Low Energy — short-range wireless protocol used as secondary channel.
- **CCM:** Counter with CBC-MAC — AES mode providing both encryption and authentication.
- **CSMA/CA:** Carrier Sense Multiple Access with Collision Avoidance — MAC protocol.
- **ECDHE:** Elliptic Curve Diffie-Hellman Ephemeral — key exchange providing forward secrecy.
- **ECDSA:** Elliptic Curve Digital Signature Algorithm.
- **ERP:** Effective Radiated Power — the power radiated by the antenna.
- **GFSK:** Gaussian Frequency Shift Keying — constant-envelope modulation.
- **HKDF:** HMAC-based Key Derivation Function.
- **KDF:** Key Derivation Function — derives keys from a shared secret.
- **LBT:** Listen-Before-Talk — channel access mechanism.
- **MICS:** Medical Implant Communication Service — 402-405 MHz band.
- **Nonce:** A number used only once — critical for AES-CTR/CCM security.
- **RSSI:** Received Signal Strength Indicator.
- **SDR:** Software-Defined Radio.
- **TRNG:** True Random Number Generator.

## 28. Flashcards

1. Q: Why is CRC not a security mechanism? A: CRC has no secret key — anyone can compute the CRC of any message. It detects accidental errors, not intentional modification.
2. Q: What is the catastrophic consequence of AES-CCM nonce reuse? A: The same keystream is produced, and XORing two ciphertexts reveals the XOR of two plaintexts.
3. Q: Why is per-command authorization important? A: Because a session may be established with low privilege (home monitoring) but the protocol must not allow high-privilege commands (clinical programming) in that session.
4. Q: What is the replay window, and what is the trade-off? A: The range of acceptable sequence numbers. Larger window = better reordering tolerance but larger replay attack surface.
5. Q: How far can an attacker eavesdrop with a directional antenna and LNA? A: 100-500 meters, depending on equipment quality. Tissue attenuation (20-40 dB) is not sufficient protection.
6. Q: What is a relay attack, and why is it hard to detect? A: Two attackers relay communication between patient and programmer. Hard to detect because the relay is transparent — both parties think they're communicating directly.
7. Q: Why is AES-128 sufficient for neurostimulators? A: The attack is not brute-force (infeasible for both AES-128 and AES-256) but protocol-level. AES-128 has lower energy cost.
8. Q: What information does a response code leak? A: Which commands are supported, which parameter values are accepted, and the device's current state — all useful for an attacker.

## 29. Interview Questions

1. "Walk me through the session establishment protocol for a neurostimulator. What are the key security properties at each step?"

2. "How would you design the nonce management for AES-CCM in an implantable device that may reboot unexpectedly?"

3. "A neurostimulator uses MICS for clinical programming and BLE for home monitoring. What cross-channel attacks would you test for?"

4. "An attacker records a legitimate programming session. Under what conditions can they replay those packets? How does your protocol prevent this?"

5. "What is the battery impact of adding AES-128-CCM to every packet? Is it worth it?"

6. "How would you detect a relay attack on a neurostimulator's MICS channel? What are the limitations of distance bounding in tissue?"

7. "Design a protocol security test suite for a new neurostimulator. What would you test first, and why?"

8. "The Abbott/St. Jude vulnerability involved an unencrypted home monitoring channel. How would you have designed the security requirements to prevent this?"

## 30. Research Questions

1. **Distance bounding in tissue:** Can we design a distance bounding protocol that works reliably through human tissue, given the variable propagation delay? What is the minimum achievable precision?

2. **Post-quantum implant protocols:** What is the minimum overhead (bandwidth, latency, energy) of adding post-quantum cryptography to an implantable device protocol? Is it feasible with current hardware?

3. **Physical layer security for implants:** Can channel state information (CSI) be used as a cryptographic key source? What is the entropy rate of the tissue channel, and is it sufficient for key generation?

4. **Protocol obfuscation resistance:** How long does it take to reverse-engineer a proprietary neurostimulator protocol using only passive observation? Can we design protocols that resist PRE for >100 hours of observation?

## 31. Books

1. **Stallings, W. (2017).** *Cryptography and Network Security.* 7th ed. Pearson. — Comprehensive cryptography reference.
2. **NIST SP 800-52 Rev. 2 (2019).** *Guidelines for the Selection, Configuration, and Use of TLS.* — While not directly about MICS, the principles apply.
3. **Zander, S. et al. (2023).** *Wireless Security: Theory and Practice.* — Wireless protocol security.
4. **Newman, H. (2021).** *Bluetooth Application Programming with the Secure and Health-Care Profiles.* — BLE security for medical devices.

## 32. Papers

1. **Halperin, D. et al. (2008).** "Pacemakers and Implantable Cardiac Defibrillators: Software Radio Attacks and Zero-Power Defenses." *IEEE S&P.*
2. **Gao, W. et al. (2022).** "Security Analysis of Implantable Medical Devices." *IEEE IoT Journal.*
3. **Li, C. et al. (2020).** "Security and Privacy of Implantable Medical Devices." *IEEE Reviews in Biomedical Engineering.*
4. **Cobb, W.E. et al. (2023).** "Firmware Security Analysis of Neural Implant Systems." *IEEE TNSRE.*
5. **Braun, B. et al. (2018).** "The Bypass of Bluetooth Low Energy Privacy: An Empirical Study." *IEEE S&P.* — BLE privacy vulnerabilities.
6. **Cao, Y. et al. (2020).** "Bluetooth Low Energy (BLE) Security: A Comprehensive Survey." *ACM Computing Surveys.*

## 33. Standards

1. **IEEE 802.15.6-2012** — Wireless Body Area Networks (includes MICS band)
2. **IEEE 802.15.1 (Bluetooth)** — BLE specification
3. **FCC Part 95** — Personal Radio Services (MICS regulations in the US)
4. **ETSI EN 301 839** — Short Range Devices (MICS regulations in Europe)
5. **FDA Guidance (2023)** — "Cybersecurity in Medical Devices"
6. **NIST SP 800-188** — Dealing with射频 (RF) Risk
7. **ISO/IEEE 11073** — Medical Device Communication Standards
8. **IEC 60601-1-2** — EMC requirements for medical electrical equipment (relevant for EMI/jamming)

## 34. Open Source Projects

1. **GNU Radio** — SDR framework for capturing and transmitting RF signals
2. **HackRF One** — Low-cost SDR hardware (1 MHz - 6 GHz)
3. **Ubertooth** — Open-source BLE monitoring platform
4. **Wireshark** — Packet analyzer with BLE and 802.15.4 dissectors
5. **scapy** — Python packet manipulation library
6. **pycryptodome** — Python cryptographic library (AES-CCM, ECDSA, HKDF)
7. **bleak** — Python BLE library for security testing
8. **gr-ieee802-15-4** — GNU Radio module for 802.15.4 (used in WBAN)

## 35. Datasets

1. **IEEE 802.15.6 Simulation Dataset** — Simulated WBAN traffic for protocol testing
2. **BLE Packet Capture Dataset** — Captured BLE traffic from medical devices (various sources)
3. **SHIELD Packet Trace Dataset** — Captured implant communication traces (limited availability)

## 36. Reading Roadmap

**Week 1:** Lesson Parts 1-2 (physical layer, packet structure, session establishment, cryptography, attacks, protocol RE)
**Week 2:** Lesson Part 3 (STRIDE, failures, VIREON integration) + Lab 001 (Protocol Simulator)
**Week 3:** Lab 002 (Protocol Attacks) + 2 challenges
**Week 4:** Deep reading of referenced papers, begin formulating research question on distance bounding

## 37. Suggested VIREON-LABS Modules (Next)

1. **NL-005:** Closed-Loop System Security — analyze how protocol latency and reliability affect the control loop
2. **NL-006:** Adversarial ML for Neural Signals — attack the ML classifiers in adaptive systems
3. **NL-007:** Digital Twin Architecture — integrate NL-004's wireless channel model into the complete digital twin

## 38. Suggested GitHub Issues

1. "Define ProtocolAnalyzer provider interface specification" — foundation for all protocol analysis providers
2. "Implement standardized protocol attack scenario library (WP-001 through WP-008)"
3. "Create MICS channel model for digital twin wireless simulation"
4. "Implement cross-channel security policy validator for MICS+BLE devices"
5. "Design protocol fingerprint database for commercially available neurostimulators"
6. "Implement battery drain measurement framework for wireless attack benchmarking"

---

## Executive Summary

Wireless protocol security is the gatekeeper for all remote interactions with neurostimulators. The unique constraints of the implant environment (MICS band, tissue channel, low power, limited bandwidth) force aggressive trade-offs between security strength and resource consumption. AES-128-CCM provides the necessary confidentiality and integrity with acceptable overhead. Session establishment must use strong pairing mechanisms and proper key derivation. Per-command authorization must be enforced to prevent privilege escalation. Replay protection through sequence number windows must be carefully designed to balance tolerance and security. The protocol layer is the first line of defense against remote attacks, and its security must be validated through comprehensive benchmarking (WP-001 through WP-008) as part of VIREON's validation framework.
