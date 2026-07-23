# NL-004 Challenges: Wireless Protocol Security

## Challenge Categories

- **CTF:** Exploit specific protocol vulnerabilities
- **VAL:** Validation and security assessment
- **RES:** Research and design
- **BENCH:** Benchmark implementation

---

## CTF-007: Session Key Extraction via Nonce Reuse

**Difficulty:** Hard | **Time:** 6-8 hours | **Vulnerability Class:** Cryptographic

### Scenario

A neurostimulator's firmware was updated and the nonce counter was accidentally reset to 0 while the session key remained the same. You have captured two data packets transmitted with the same nonce but different payloads.

### Objective

1. Modify Lab 001's `CryptoEngine.encrypt()` to allow nonce reuse (add a test hook).
2. Capture two packets encrypted with the same nonce and key.
3. XOR the two ciphertexts to recover the XOR of the two plaintexts.
4. Given that one plaintext is a known command (e.g., `GET_STATUS` = `0x01`), recover the other plaintext.
5. Extend the attack: how many known-plaintext pairs are needed to fully recover the keystream?

### Deliverable

A Python script demonstrating the nonce-reuse attack with a writeup explaining each step and the mathematical basis.

### VIREON Mapping

- Benchmark: WP-001 (extends cleartext detection to partial key recovery)
- Provider: `NonceReuseDetector` — analyzes nonce uniqueness across packet captures

### Hints

- In CTR mode (which CCM uses internally), `C1 = P1 XOR KS` and `C2 = P2 XOR KS`, so `C1 XOR C2 = P1 XOR P2`.
- If P1 is known, then `P2 = C1 XOR C2 XOR P1`.
- The keystream repeats every 32 bytes (SHA-256 digest size). Packets longer than 32 bytes have repeating keystream.

---

## CTF-008: Relay Attack Implementation

**Difficulty:** Hard | **Time:** 8-10 hours | **Vulnerability Class:** Protocol Design

### Scenario

An attacker wants to manipulate a patient's neurostimulator from a remote location. The MICS protocol requires proximity (<2m), but the attacker has two radios: one near the patient and one near a stolen clinic programmer.

### Objective

1. Implement a relay proxy that sits between a ProgrammerProtocol and ImplantProtocol:
   - Receives packets from the programmer, forwards to implant
   - Receives packets from implant, forwards to programmer
   - Adds configurable latency (10-500ms)
2. Test whether the protocol's challenge-response timeout accepts the relayed communication.
3. Implement a distance bounding check: the implant measures round-trip time and rejects responses >50ms.
4. Evaluate the effectiveness of distance bounding against the relay (consider tissue propagation delay variability of 5-15ms).

### Deliverable

A `relay_attack.py` script with the relay proxy, timing measurements, and a distance bounding implementation. Writeup analyzing the minimum detectable relay distance.

### VIREON Mapping

- Benchmark: New relay detection benchmark (extends WP-002/003)
- Provider: `RelayDetector` — analyzes timing patterns in session establishment

### Hints

- The challenge-response in Lab 001 has no explicit timeout — this IS the vulnerability.
- Real tissue propagation delay at MICS frequencies: ~5 ns/m in air, ~10-20 ns/m in tissue (negligible).
- The relay latency is dominated by the radio link between the two attackers (typically 10-100ms over WiFi, 1-10ms over dedicated radio).
- Distance bounding precision is limited by clock resolution (Cortex-M4 timer: ~30ns, but software overhead: ~10us).

---

## VAL-007: Protocol Fingerprinting from Packet Timing

**Difficulty:** Medium | **Time:** 4-6 hours | **Vulnerability Class:** Information Disclosure

### Scenario

You intercept a MICS-band transmission but cannot decode the packets (encrypted). You need to identify the device type and protocol version from external characteristics alone.

### Objective

1. Capture packet timing data from Lab 001's session mode (timestamps from packet_record).
2. Extract timing features: inter-packet intervals, session establishment duration, response latency distribution.
3. Compare timing profiles between:
   - Normal session (Lab 001 --mode session)
   - Attack scenario (Lab 002 WP-006 flooding)
   - Different command mixes
4. Build a simple classifier (threshold-based) that identifies the session type from timing alone.
5. Evaluate whether timing information leaks command types (e.g., OTA_UPDATE takes longer due to larger payloads).

### Deliverable

A `protocol_fingerprinter.py` script with timing feature extraction and classification. Writeup analyzing the information leakage through timing.

### VIREON Mapping

- Provider: `ProtocolFingerprinter` — identifies device protocol from packet capture
- Benchmark: Extends WP-001 (traffic analysis beyond ciphertext inspection)

### Hints

- Session establishment timing is dominated by crypto operations (KDF: ~5ms equivalent in simulation).
- Command response time varies with payload size (encryption + transmission).
- The EnergyModel in Lab 001 provides per-operation energy costs that correlate with timing.

---

## VAL-008: Cross-Channel Attack Analysis

**Difficulty:** Medium | **Time:** 5-7 hours | **Vulnerability Class:** Architecture

### Scenario

A neurostimulator supports both MICS (clinical) and BLE (home monitoring). You need to evaluate whether cross-channel attacks are possible.

### Objective

1. Design a threat model for the dual-channel architecture (NL-004 Section 16).
2. Implement a `DualChannelSimulator` that maintains two separate protocol stacks (MICS + BLE) connected to the same implant state.
3. Test the following cross-channel attacks:
   - Send conflicting commands on both channels simultaneously
   - Establish a MICS session while a BLE session is active
   - Extract the MICS pairing key through a BLE-side vulnerability
4. Evaluate the cross-channel security policies from Section 16.2 (MICS priority, shared session lock, independent keys).

### Deliverable

A `dual_channel_test.py` script implementing the dual-channel simulator and attack tests. Writeup with recommended cross-channel policies.

### VIREON Mapping

- Provider: `CrossChannelAnalyzer` — tests for dual-channel vulnerabilities
- Digital Twin: Extends the wireless channel model for multi-channel simulation

### Hints

- The key question: do MICS and BLE share any state? (session key, therapy parameters, safety monitor)
- The Medtronic Conexus protocol had cross-channel issues between the programming and monitoring channels.
- A shared session lock is the simplest mitigation — only one session at a time.

---

## RES-007: Distance Bounding Protocol Design

**Difficulty:** Expert | **Time:** 10-15 hours | **Research Category:** Protocol Design

### Scenario

Distance bounding is the primary known defense against relay attacks on implant communication. However, no standardized distance bounding protocol exists for the MICS band. Design one.

### Objective

1. Research existing distance bounding protocols ( Brands-Chaum, Hancke-Kuhn, Swiss-Knife).
2. Design a distance bounding protocol optimized for the MICS environment:
   - Must work through human tissue (variable propagation delay)
   - Must be computationally feasible on Cortex-M4
   - Must not add significant latency to session establishment
   - Must handle the MICS LBT (listen-before-talk) constraint
3. Implement a simulation of the protocol and measure:
   - Minimum detectable relay distance
   - False acceptance rate (relay accepted as legitimate)
   - False rejection rate (legitimate session rejected)
4. Analyze the impact of tissue propagation delay variability on precision.

### Deliverable

A research report (3-5 pages) with protocol specification, simulation code, and analysis. Include a comparison table with existing distance bounding protocols.

### VIREON Mapping

- Provider: `DistanceBoundingValidator` — new VIREON provider
- Research: Directly addresses NL-004 Research Question 1 (distance bounding in tissue)
- Benchmark: New WP-009 (relay resistance)

---

## RES-008: Post-Quantum Protocol Upgrade Analysis

**Difficulty:** Expert | **Time:** 8-12 hours | **Research Category:** Cryptography

### Scenario

NIST has standardized post-quantum cryptographic algorithms (ML-KEM/Kyber, ML-DSA/Dilithium). A neurostimulator manufacturer wants to evaluate the feasibility of upgrading their protocol to be quantum-resistant.

### Objective

1. Analyze the computational cost of ML-KEM-768 (key encapsulation) on Cortex-M4:
   - Key generation time and energy
   - Encapsulation/decapsulation time and energy
   - Code size and RAM requirements
2. Compare with current ECDH P-256 (the most likely pre-quantum alternative).
3. Design a hybrid key exchange protocol (ECDH + ML-KEM) for forward secrecy that degrades gracefully if ML-KEM is too expensive.
4. Calculate the impact on:
   - Session establishment latency
   - Battery life (energy per session)
   - Firmware size (flash and RAM)
   - MICS bandwidth overhead (public key sizes)

### Deliverable

A research report (3-5 pages) with performance analysis, protocol design, and recommendations. Include a table comparing pre-quantum, post-quantum, and hybrid options.

### VIREON Mapping

- Provider: `PostQuantumAnalyzer` — evaluates quantum resistance of protocol
- Research: Addresses NL-004 Research Question 2 (post-quantum feasibility)

---

## BENCH-007: Protocol Fuzzing Framework

**Difficulty:** Medium | **Time:** 5-7 hours | **Benchmark Implementation**

### Scenario

VIREON needs a standardized protocol fuzzing framework that can test any neurostimulator protocol implementation.

### Objective

1. Design a fuzzing framework that mutates valid protocol packets:
   - Bit flipping (single and multi-bit)
   - Byte substitution (random and targeted)
   - Length manipulation (truncation, extension)
   - Field-specific mutations (change packet type, sequence number, address)
2. Implement the fuzzer as a `ProtocolFuzzer` class that takes an `ImplantProtocol` and generates mutated packets.
3. Run the fuzzer for 10,000 iterations and collect:
   - Crash rate (exceptions raised)
   - Authentication failure rate
   - Response code distribution
   - State machine transition coverage
4. Compare crash rates between secure and vulnerable configurations.

### Deliverable

A `protocol_fuzzer.py` script with the fuzzer implementation and a report analyzing the results.

### VIREON Mapping

- Provider: `PacketFuzzer` — standardized fuzzing provider for VIREON
- Benchmark: Extends WP-004 (beyond forged auth tags to systematic mutation)

---

## BENCH-008: Energy Side-Channel Analysis

**Difficulty:** Hard | **Time:** 6-8 hours | **Benchmark Implementation**

### Scenario

Different protocol operations consume different amounts of energy. An attacker who can measure the implant's energy consumption (through power analysis) might infer which operations are being performed.

### Objective

1. Use Lab 001's `EnergyModel` to profile energy consumption for each operation type:
   - Session establishment
   - Command reception and processing
   - Cryptographic operations (encrypt, decrypt, KDF)
   - State transitions
2. Determine whether the energy differences between operations are distinguishable:
   - Calculate the signal-to-noise ratio for each operation class
   - Estimate the number of measurements needed for reliable classification
3. Design a countermeasure: add energy-padding to make all operations consume the same energy.
4. Implement the countermeasure in the `EnergyModel` and re-evaluate.

### Deliverable

A `energy_analysis.py` script with energy profiling, classification analysis, and countermeasure evaluation.

### VIREON Mapping

- Provider: `EnergySideChannelAnalyzer` — detects energy-based information leakage
- Benchmark: New WP-010 (energy side-channel resistance)
- Research: Extends NL-004 Section 7.4 (battery drain) to side-channel analysis

---

## Selection Guide

| Goal | Recommended Challenges |
|---|---|
| Understand protocol exploitation | CTF-007, CTF-008 |
| Build validation skills | VAL-007, VAL-008 |
| Conduct original research | RES-007, RES-008 |
| Contribute to VIREON | BENCH-007, BENCH-008 |
| Maximum learning breadth | CTF-007 + VAL-007 + BENCH-007 |
| Research track | RES-007 + BENCH-008 |
