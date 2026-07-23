# NL-004: Wireless Protocol Security for Neurostimulators (Part 1)

## 1. The Wireless Link as Primary Attack Surface

### 1.1 Why Wireless Is the Gate

Among all the attack surfaces of a neurostimulator — firmware, hardware, supply chain, physical access — the wireless link is unique in three ways: it is the only attack surface accessible to a remote attacker without physical contact, it is the only attack surface that exists by design (the device must communicate wirelessly to fulfill its clinical purpose), and it is the only attack surface that the patient cannot control or mitigate through their own behavior.

A patient can choose not to connect to untrusted WiFi networks on their phone. A patient cannot choose whether their neurostimulator's wireless interface is active — it must be active to receive therapy programming and to transmit diagnostic data. The wireless link is always on (or at least always capable of being activated by an external programmer), and the patient has no visibility into what is being communicated.

This makes wireless protocol security the single most important layer of defense for the patient. If the protocol is secure, a remote attacker cannot modify therapy, exfiltrate neural data, or drain the battery. If the protocol is insecure, all of these attacks are possible from a distance.

### 1.2 The Tissue Channel

Unlike conventional wireless systems where the channel is air, the implant wireless channel passes through biological tissue. This has profound implications for protocol design and security:

**Path loss:** The human body attenuates RF signals by 20-40 dB at MICS frequencies (402-405 MHz), depending on the implant depth, tissue composition, and body posture. At 2.4 GHz (BLE), the attenuation is even higher (30-50 dB). This limits the effective communication range to centimeters for MICS (1-5 cm typical, up to 2 meters with a good external antenna) and similarly limited for BLE.

**Multipath fading:** RF signals passing through tissue reflect off tissue boundaries (skin-fat-muscle-bone interfaces), creating multipath interference. The signal strength fluctuates as the patient moves, causing intermittent packet loss that the protocol must handle through retransmission.

**Antenna constraints:** The implant antenna must be small (typically a coil antenna, 10-30 mm diameter) and is tuned for the specific frequency band. The antenna's radiation pattern is affected by the surrounding tissue, creating directionality that an attacker can potentially exploit (communication is more reliable from certain body positions).

**Security implication of the tissue channel:** The limited range provides a degree of physical security — an attacker must be within meters of the patient. However, this "security through proximity" is weak: an attacker can achieve longer range with a directional antenna and a sensitive receiver (SDR with LNA). The Abbott/St. Jude vulnerability demonstrated that an attacker with reasonable equipment could communicate with an implant from 10 meters away.

### 1.3 Protocol Layers and Security Responsibilities

```
┌─────────────────────────────────┐
│  Application Protocol          │  Therapy commands, diagnostics
│  - Command types               │  SECURITY: per-command auth
│  - Parameter sets              │  SECURITY: parameter validation
│  - Status queries               │  SECURITY: response integrity
├─────────────────────────────────┤
│  Security Layer                │  Encryption + authentication
│  - Authenticated encryption    │  SECURITY: confidentiality
│  - Key management              │  SECURITY: integrity
│  - Session management          │  SECURITY: authenticity
├─────────────────────────────────┤
│  Transport Layer               │  Segmentation, reassembly, flow
│  - Packet fragmentation        │  SECURITY: reassembly buffer overflow
│  - Acknowledgment/retry        │  SECURITY: ACK spoofing
│  - Flow control                │  SECURITY: resource exhaustion
├─────────────────────────────────┤
│  MAC Layer                     │  Framing, addressing, CRC
│  - Frame structure             │  SECURITY: CRC is not authentication
│  - Device addressing           │  SECURITY: address spoofing
│  - Channel access              │  SECURITY: DoS through contention
├─────────────────────────────────┤
│  Physical Layer                │  Modulation, frequency, power
│  - MICS (402-405 MHz)          │  SECURITY: EMI injection, jamming
│  - BLE (2.4 GHz)               │  SECURITY: frequency hopping
│  - Proprietary                 │  SECURITY: unknown vulnerabilities
└─────────────────────────────────┘
```

Each layer introduces its own attack surface. A comprehensive protocol security analysis must evaluate each layer independently and then evaluate the composition of layers (because vulnerabilities at one layer can amplify vulnerabilities at another).

## 2. MICS Band: Physical Layer Characteristics

### 2.1 MICS Band Specification

The Medical Implant Communication Service (MICS) band is an internationally allocated frequency band specifically for medical implant communication:

| Parameter | Value | Security Relevance |
|---|---|---|
| Frequency range | 402-405 MHz | Narrow band limits bandwidth but provides regulatory protection |
| Bandwidth | 3 MHz | Limits data rate (250-800 kbps typical) |
| Channel spacing | 100-300 kHz | Multiple channels enable frequency diversity |
| Max ERP | 25 uW (-16 dBm) | Very low power limits range and eavesdropping distance |
| Modulation | GFSK (typical) | Constant-envelope modulation simplifies PA design |
| Channel access | Listen-before-talk (LBT) | Collision avoidance, not a security mechanism |
| Duty cycle | Varies by region | Some regions require <10% duty cycle |

### 2.2 Why MICS Matters for Security

The MICS band's physical characteristics directly constrain the security design:

**Low power limits eavesdropping range:** At 25 uW ERP, the signal at 10 meters is approximately -76 dBm (in free space; less through tissue). An attacker would need a sensitive receiver (SDR with LNA, noise figure < 3 dB) to detect the signal at that range. At 1 meter, the signal is approximately -56 dBm, easily detectable with consumer-grade equipment. This means that the primary eavesdropping threat is from close proximity (same room, adjacent bed in hospital).

**Narrow bandwidth limits data rate:** At 250-800 kbps, the protocol must be efficient. Every byte of security overhead (encryption headers, authentication tags, nonces) reduces the available bandwidth for clinical data. This forces designers to minimize security overhead, potentially at the expense of security strength.

**LBT provides no security:** Listen-before-talk prevents the implant from transmitting when the channel is occupied by another MICS device. An attacker who transmits continuously on the MICS channel can prevent the implant from communicating (jamming/DoS). LBT is a medium access control mechanism, not a security mechanism.

### 2.3 MICS Channel Model

For VIREON's digital twin, the MICS channel can be modeled as:

```
P_rx = P_tx + G_tx + G_rx - PL_path - PL_tissue - PL_fading - PL_misc

Where:
  P_tx = -16 dBm (25 uW ERP)
  G_tx = -10 to 0 dBi (implant antenna, small coil)
  G_rx = 0 to 6 dBi (external antenna)
  PL_path = 20*log10(4*pi*d/lambda) (free space path loss)
  PL_tissue = 20-40 dB (frequency and depth dependent)
  PL_fading = 0-20 dB (multipath, body movement)
  PL_misc = 2-5 dB (matching loss, cable loss)
```

**Security implication:** The variable tissue loss and fading mean that the attacker's ability to communicate depends on the patient's body position, the implant depth, and the tissue composition. An attacker cannot guarantee communication at any specific range. Protocol security must assume that the attacker CAN communicate (worst case), but should also consider that the legitimate programmer may NOT be able to communicate reliably (fading), requiring the protocol to be robust to intermittent connectivity.

### 2.4 Comparison: MICS vs BLE vs Proprietary

| Characteristic | MICS (402 MHz) | BLE (2.4 GHz) | Proprietary |
|---|---|---|---|
| Regulatory status | Medical band, global | ISM band, global | Varies |
| Bandwidth | 3 MHz | 80 MHz | Varies |
| Data rate | 250-800 kbps | 1-2 Mbps | Varies |
| Range (implant) | 1-200 cm | 1-50 cm | Varies |
| Encryption | Custom (per manufacturer) | AES-CCM (standard) | Unknown |
| Authentication | Custom | Pairing + bonding | Unknown |
| Power consumption | Very low | Low | Varies |
| Standardization | IEEE 802.15.6-based | Bluetooth 5.x | None |
| Security analysis | Limited (proprietary) | Extensive (public standard) | None |

**Security implication:** BLE benefits from extensive public security analysis — the Bluetooth specification is publicly available, and the security mechanisms have been studied by thousands of researchers. MICS protocols, being proprietary, have received far less analysis. This is a double-edged sword: proprietary protocols may have unknown vulnerabilities (security through obscurity), but they also present a higher barrier to attackers who must reverse-engineer the protocol before attacking it. VIREON's approach is to enable standardized security assessment regardless of whether the protocol is standard or proprietary.

## 3. Packet Structure and Framing

### 3.1 Generic Neurostimulator Packet Format

While each manufacturer's protocol is different, most neurostimulator wireless packets follow a common structure:

```
┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│ Preamble │ Sync     │ Header   │ Payload  │ Auth Tag │ CRC      │
│ (2-4 B)  │ (1-2 B)  │ (4-8 B)  │ (0-256B) │ (4-16 B) │ (2-4 B)  │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘

Preamble:  Alternating 0/1 pattern for receiver synchronization
Sync:      Fixed pattern marking the start of the frame
Header:    Length, packet type, sequence number, device address
Payload:   Encrypted command/telemetry data
Auth Tag:  Cryptographic authentication (AES-CCM tag, HMAC, etc.)
CRC:       Error detection (CRC-16 or CRC-32)
```

### 3.2 Header Fields and Security

A typical header contains the following fields:

| Field | Size | Purpose | Security Concern |
|---|---|---|---|
| Packet type | 1 byte | Command, response, ACK, telemetry | Unauthenticated type field enables type confusion attacks |
| Sequence number | 2 bytes | Packet ordering, replay detection | 16-bit seq wraps after 65536 — replay window management |
| Payload length | 1-2 bytes | Indicates payload size | If unauthenticated, attacker can modify to cause buffer overflow |
| Device address | 2-4 bytes | Identifies the target implant | Address spoofing enables targeted attacks |
| Flags | 1 byte | Encryption, fragmentation, priority | Flag manipulation changes protocol behavior |

**Critical design principle:** The authentication tag MUST cover the header AND the payload. If the authentication tag only covers the payload, an attacker can modify the header fields (packet type, length, flags) without invalidating the authentication. This would allow header manipulation attacks: changing the packet type to bypass routing, changing the length to cause buffer overflows, or changing the address to redirect packets.

### 3.3 CRC vs. Authentication

A common confusion in protocol security is the role of CRC (Cyclic Redundancy Check). CRC is an error detection mechanism, NOT a security mechanism:

- **CRC detects accidental errors:** Bit flips caused by noise, interference, or hardware faults.
- **CRC does NOT detect intentional modification:** An attacker who knows the CRC polynomial can compute the correct CRC for any modified packet.
- **CRC is NOT a MAC (Message Authentication Code):** CRC has no secret key. Anyone can compute the CRC of any message.

However, CRC still has a security role: if the protocol includes an authentication tag (e.g., AES-CCM), the CRC provides a fast pre-check before the expensive cryptographic verification. Packets with incorrect CRCs are discarded immediately without cryptographic processing, saving battery and processing time. The CRC must be computed AFTER the authentication tag (so CRC errors don't cause the receiver to skip security verification of valid packets).

### 3.4 Fragmentation and Reassembly

Large payloads (e.g., firmware updates, diagnostic data dumps) must be fragmented into multiple packets. The reassembly process is a security-critical operation:

**Fragmentation header:** Each fragment includes: total length, fragment offset, fragment index, and a fragment ID.

**Reassembly vulnerability:** The receiver must allocate a buffer large enough for the complete reassembled payload. If the total length field is unauthenticated, an attacker can modify it to cause the receiver to allocate a very large buffer (memory exhaustion) or to write fragment data beyond the buffer boundary (buffer overflow). This is exactly the vulnerability class exploited in many IP fragmentation attacks (e.g., the Ping of Death).

**Out-of-order fragment attack:** If fragments can arrive out of order, an attacker can inject a malicious fragment that overlaps with legitimate fragments. The receiver's behavior when fragments overlap (overwrite, reject, or combine) determines the vulnerability's severity.

## 4. Session Establishment and Key Management

### 4.1 Pairing: The Root of Trust for Wireless

Pairing is the process of establishing a shared secret between the implant and the programmer. This shared secret is the root of all subsequent session security. If the pairing secret is compromised, all session security is broken.

**Pairing methods used in neurostimulators:**

1. **Proximity pairing:** The programmer must be within a few centimeters of the implant. The implant verifies proximity by measuring the received signal strength (RSSI) — only a very close programmer can produce a strong enough signal. The pairing secret is derived from a random value exchanged during the proximity session.

2. **Wired pairing:** The programmer connects to the implant via a wired interface (inductive coupling through the skin) during implantation surgery. This provides the strongest security because the pairing secret is exchanged over a physical connection that cannot be intercepted wirelessly.

3. **Pre-provisioned pairing:** The pairing secret is programmed into both devices at the factory. This is the weakest method because the secret exists in the supply chain and could be extracted during manufacturing, shipping, or storage.

4. **Password-based pairing:** The clinician enters a password (printed on the device packaging or known to the clinic) into the programmer. The password is used to derive the pairing secret. This is vulnerable to password guessing, especially if the password is short or printed on accessible materials.

### 4.2 Session Establishment Protocol

A typical session establishment protocol for a neurostimulator:

```
Programmer              Implant
   │                       │
   │  1. Session Request    │
   │  (device ID, random1)  │
   │ ────────────────────> │
   │                       │
   │  2. Challenge          │
   │  (random2)             │
   │ <──────────────────── │
   │                       │
   │  3. Response           │
   │  (MAC(pairing_key,     │
   │   random1 || random2)) │
   │ ────────────────────> │
   │                       │
   │  4. Session Key Deriv.  │
   │  Both sides derive:    │
   │  session_key = KDF(    │
   │    pairing_key,       │
   │    random1, random2)   │
   │                       │
   │  5. Encrypted Comm.    │
   │  (All subsequent      │
   │   packets use         │
   │   session_key)        │
   │ <────────────────────> │
```

### 4.3 Session Protocol Vulnerabilities

**Replay of session request:** If an attacker records the session request (step 1) and replays it later, the implant will generate a new challenge. The replayed session request itself is not directly exploitable, but it initiates a session that consumes the implant's processing resources (DoS through session flooding).

**Weak random numbers:** If `random1` or `random2` is predictable (e.g., a counter, a low-entropy PRNG, or a timestamp), the session key becomes predictable. An attacker who can predict the random values can compute the session key and decrypt all traffic. Implant firmware often uses hardware RNGs that may have limited entropy (especially if the hardware RNG is a simple LFSR).

**Static pairing key:** If the same pairing key is used for all sessions (which it is, since the pairing key is long-lived), compromising the pairing key enables the attacker to establish sessions at any time. This is a fundamental limitation of pre-shared key protocols: the key must be stored securely in both devices.

**No forward secrecy:** In the protocol above, if the pairing key is compromised, all past session keys can be derived from recorded session establishment messages (the random values are transmitted in the clear). This means an attacker who records encrypted traffic and later compromises the pairing key can decrypt all past sessions. Forward secrecy (using ephemeral key exchange like ECDHE) prevents this but adds computational overhead and protocol complexity.

**Challenge-response without mutual authentication:** The protocol above authenticates the programmer to the implant (the programmer proves knowledge of the pairing key in step 3), but does NOT authenticate the implant to the programmer. An attacker who impersonates the implant (using a fake implant or a relay attack) can establish a session with the programmer and extract the pairing key or session key. True mutual authentication requires the implant to also prove knowledge of the pairing key.

### 4.4 Key Derivation

The session key must be derived from the pairing key and the session nonces using a Key Derivation Function (KDF):

```
session_key = KDF(pairing_key, random1 || random2 || "VIREON-session-v1")

Where KDF = HKDF-SHA256 (recommended) or a custom KDF
```

**Security requirements for the KDF:**
- **Pseudorandomness:** The output must be computationally indistinguishable from random.
- **Uniqueness:** Different sessions must produce different keys, even if the pairing key is the same.
- **Independence:** Knowledge of one session key must not enable computation of other session keys.
- **No key separation failure:** The KDF must produce independent keys for different purposes (encryption, authentication, IV generation) even from the same input.

**VIREON validation:** VIREON should verify that the KDF produces unique keys for 10,000 sequential sessions (no collisions), that the keys pass statistical randomness tests, and that knowledge of one session key does not enable prediction of the next.

## 5. Cryptographic Mechanisms

### 5.1 Authenticated Encryption

Neurostimulator protocols typically use Authenticated Encryption with Associated Data (AEAD). The most common choice is AES-CCM (Counter with CBC-MAC):

**AES-CCM operation:**
1. Generate a nonce (12 bytes, unique per packet)
2. Compute CBC-MAC over the header (associated data) and payload to produce the authentication tag
3. Encrypt the payload using AES in CTR mode using the same key
4. Transmit: header (plaintext) + encrypted payload + authentication tag

**Security properties:**
- **Confidentiality:** The payload is encrypted. An eavesdropper cannot read the command or telemetry data.
- **Integrity:** The authentication tag covers both header and payload. Any modification is detected.
- **Authenticity:** Only a party with the session key can generate a valid authentication tag.

**AES-CCM vulnerabilities:**
- **Nonce reuse:** If the same nonce is used with the same key for two different messages, AES-CTR produces the same keystream for both. XORing the two ciphertexts reveals the XOR of the two plaintexts. This is a catastrophic failure. The nonce MUST be unique per packet.
- **Tag length:** Shorter authentication tags (4 bytes vs. 16 bytes) reduce the probability of detecting a forgery. An 8-byte tag provides 2^64 possible values, giving a forgery probability of 2^-64 per attempt — sufficient. A 4-byte tag gives 2^-32, which may be insufficient against a determined attacker.
- **Associated data boundaries:** The protocol must clearly define which bytes are associated data (authenticated but not encrypted) and which are payload (authenticated and encrypted). Misclassification can leave critical fields unauthenticated.

### 5.2 AES-128 vs AES-256

| Property | AES-128 | AES-256 |
|---|---|---|
| Key size | 16 bytes | 32 bytes |
| Encryption time (Cortex-M4) | ~0.5 us/block | ~0.7 us/block |
| Energy per block (Cortex-M4) | ~0.05 uJ | ~0.07 uJ |
| Security margin (as of 2025) | Adequate | Very high |
| Key storage overhead | 16 bytes in flash | 32 bytes in flash |

**Recommendation for neurostimulators:** AES-128 is sufficient for the threat model. The primary attack vector is not brute-forcing the AES key (computationally infeasible for both key sizes) but rather attacking the protocol (replay, nonce reuse, key extraction through side-channels). AES-128 provides the same resistance to these attacks as AES-256, with lower computational and energy cost. The 16-byte key storage saving is significant in devices with 256 KB of flash.

### 5.3 Public-Key Cryptography

Some neurostimulator protocols use public-key cryptography (ECDSA) for firmware signing (NL-003 Section 6) and, less commonly, for session establishment (ECDHE key exchange for forward secrecy).

**ECDSA P-256 on Cortex-M4:**
- Signature generation: ~20-50 ms (hardware-dependent)
- Signature verification: ~40-80 ms
- Key size: 32 bytes (private), 64 bytes (public + signature)

**Security implication:** ECDSA operations are 100-1000x slower than AES. This makes them impractical for per-packet operations but acceptable for per-session operations (session establishment, firmware signing). The high computational cost is one reason most neurostimulator protocols use symmetric-key cryptography (AES) for data protection and reserve public-key cryptography for infrequent operations.

### 5.4 Cryptographic Implementation Pitfalls

1. **Constant-time comparison:** When comparing authentication tags, the comparison MUST be constant-time. A non-constant-time comparison (e.g., `memcmp` that returns on the first mismatch) leaks information about the expected tag through timing. An attacker who can measure the comparison time can determine how many bytes of the forged tag are correct, enabling a byte-by-byte attack on the tag.

2. **Key whitening:** Storing the encryption key in a simple form in flash makes it extractable through firmware dump. Some devices XOR the key with a device-specific value (key whitening) before storage. This provides minimal security (the whitening value is also in firmware and can be extracted), but it does prevent trivial pattern-matching attacks on the firmware binary.

3. **IV/nonce generation:** The nonce must be unpredictable and unique. A counter is the simplest approach (increment per packet), but if the device resets and the counter restarts from 0, nonces will be reused. The counter must be stored in non-volatile memory or initialized from a random value at boot.

4. **Padding oracle:** If the protocol returns different error messages for "decryption failed" vs. "authentication failed," an attacker can use the difference to perform a padding oracle attack (applicable to CBC mode, not CTR mode). AES-CCM does not use padding, so this specific attack does not apply, but the general principle of not leaking error details applies.

## 6. Protocol State Machines

### 6.1 Implant Protocol State Machine

The implant's wireless protocol operates as a state machine:

```
         ┌──────────┐
         │  SLEEP    │
         │  (RF off) │
         └────┬─────┘
              │ RF wake signal
              v
         ┌──────────┐     No session      ┌──────────┐
         │  IDLE     │ <───────────────── │  ACTIVE   │
         │  (listen) │                     │  (session) │
         └────┬─────┘                     └────┬─────┘
              │ Valid session request          │
              v                                │ Session end /
         ┌──────────┐     Auth success     │ Timeout
         │  AUTH     │ ──────────────>     │
         │  (challenge│                   │
         │   /resp)  │                     │
         └──────────┘                     │
```

### 6.2 State Machine Attacks

**Forced state transition:** An attacker who sends a valid session request can force the implant from SLEEP to IDLE to AUTH state. Each state transition consumes energy (waking the RF receiver, processing the request). Repeatedly forcing state transitions is a battery drain attack.

**Stuck in ACTIVE state:** If the session termination logic has a bug, the implant may remain in the ACTIVE state indefinitely, continuously powering the RF receiver and draining the battery. An attacker can exploit this by establishing a session and then disconnecting without sending a proper termination message.

**Auth state timeout:** The implant must have a timeout in the AUTH state. If the programmer sends a session request but never responds to the challenge, the implant should return to IDLE after a timeout. If the timeout is too long (e.g., 30 seconds), an attacker can consume the implant's processing resources for that duration. If the timeout is too short (e.g., 100 ms), legitimate programmers with slow cryptographic operations may fail to complete authentication.

### 6.3 Sequence Number Management

Sequence numbers prevent replay attacks by ensuring that each packet is fresh. The receiver maintains a "replay window" — a range of acceptable sequence numbers. Packets with sequence numbers outside the window are rejected.

**Sliding window approach:**
```
Receiver window: [N-W+1, N]  where N = highest received seq, W = window size

Incoming packet with seq S:
  If S > N:           ACCEPT (advance window: [S-W+1, S])
  If S in [N-W+1, N]: ACCEPT (retransmission, already seen)
  If S < N-W+1:      REJECT (too old, replay attack)
```

**Security implications:**
- **Window size:** A larger window (e.g., W=64) provides better tolerance for packet reordering but increases the replay window. An attacker can replay any of the last W packets. A smaller window (e.g., W=8) reduces the replay window but may cause legitimate retransmissions to be rejected.
- **Sequence number rollover:** 16-bit sequence numbers wrap at 65535 to 0. The replay window must handle the rollover correctly (modular arithmetic). A bug in rollover handling can cause the window to reject all packets after rollover (DoS) or to accept all packets (replay vulnerability).
- **Per-session vs. per-device:** If the sequence counter resets to 0 at the start of each session, an attacker who replays packets from a previous session will have sequence numbers in the valid range. The sequence counter MUST be unique across sessions (e.g., combined with a session ID).

## 7. Protocol-Level Attacks

### 7.1 Attack Taxonomy

| Attack | Layer | Prerequisite | Impact | Detection Difficulty |
|---|---|---|---|---|
| **Eavesdropping** | Physical | SDR within range | Neural data exposure | Medium (requires proximity) |
| **Packet injection** | MAC | Knowledge of packet format | Command injection | Easy (if no encryption) |
| **Replay** | Transport | Recorded legitimate session | Command replay | Medium (sequence numbers help) |
| **Desynchronization** | Transport | Modify seq numbers | Session disruption | Easy |
| **ACK spoofing** | Transport | Predict ACK format | False delivery confirmation | Easy |
| **Command flooding** | MAC | Ability to transmit | DoS (processing/battery) | Easy |
| **Selective jamming** | Physical | Directional antenna | Targeted DoS | Hard (requires equipment) |
| **Session hijacking** | Security | Compromised session key | Full session control | Hard (requires key compromise) |
| **Battery drain** | All | Ability to transmit | Premature battery depletion | Medium |
| **Relay attack** | Physical | Two radios (near patient + near programmer) | Man-in-the-middle | Hard |
| **Firmware injection** | Application | Valid firmware signature | Persistent compromise | Very hard |

### 7.2 Replay Attack in Detail

The replay attack is the most protocol-relevant attack for neurostimulators because it requires no cryptographic weakness — only the ability to record and retransmit legitimate packets.

**Attack scenario:**
1. Attacker records a legitimate programming session (e.g., in a hospital or clinic) using an SDR.
2. Attacker later approaches the patient and retransmits the recorded packets.
3. If the protocol uses per-session sequence numbers, the replayed packets have the wrong sequence numbers and are rejected.
4. If the protocol does not use sequence numbers, or if the sequence counter has wrapped, the replayed packets are accepted.

**Replay detection mechanisms:**
1. **Sequence numbers (per-session):** Each session starts with a fresh sequence counter. Recorded packets from a previous session have stale sequence numbers.
2. **Timestamps:** Include a timestamp in each packet. Reject packets with timestamps too far in the past. Requires clock synchronization between programmer and implant.
3. **Challenge-response:** The implant issues a unique challenge at session start. The programmer must include the challenge in all subsequent packets. Recorded packets from a different session have the wrong challenge.
4. **Freshness tokens:** The implant generates a one-time token for each command. The programmer must include the token in the response. Tokens cannot be reused.

**Replay detection limitations:**
- Per-session sequence numbers are effective against cross-session replay but NOT against within-session replay (replaying a packet from the current session with a valid sequence number). Within-session replay is only detectable if the receiver tracks which specific packets it has already seen.
- Timestamps require clock synchronization, which is difficult for battery-powered implants (clocks drift over time). A loose timestamp window (e.g., 5 minutes) provides limited replay protection.

### 7.3 Desynchronization Attack

The desynchronization attack targets the sequence number synchronization between the programmer and the implant:

1. The attacker transmits a burst of packets with forged sequence numbers (e.g., all with seq=65535, the maximum 16-bit value).
2. If the implant accepts the forged packets and advances its expected sequence number, the legitimate programmer's subsequent packets (with lower sequence numbers) are rejected.
3. The legitimate session is disrupted — the programmer and implant are desynchronized.
4. The only recovery is to terminate the session and establish a new one, which costs time and energy.

**Mitigation:** The replay window (Section 6.3) provides some protection: forged packets with sequence numbers far outside the window are rejected. However, an attacker who knows the current window position can craft forged packets within the window that advance the expected sequence number.

### 7.4 Battery Drain Attack

The battery drain attack exploits the implant's need to respond to wireless communication:

1. **RF wake attack:** Transmit a continuous signal on the MICS channel. The implant's RF receiver detects the signal, wakes up, and attempts to decode packets. Decoding garbage consumes processing energy. The continuous wake prevents the implant from entering low-power sleep mode.

2. **Session flood attack:** Rapidly establish and terminate sessions. Each session establishment requires the implant to generate random numbers, compute cryptographic operations, and power the RF transceiver. Each session consumes approximately 0.1-1 mJ of energy. At 10 sessions/second, this is 1-10 mW — comparable to the device's active power consumption.

3. **ACK flood attack:** Transmit packets that require acknowledgment. The implant must power its transmitter to send ACKs, consuming significantly more energy than receiving alone. Transmitting at MICS power levels (25 uW ERP) typically consumes 10-50 mW of battery power.

**Detection:** Unusual power consumption can be detected by the firmware's power management subsystem (NL-003 Section 12). If the power consumption exceeds the expected profile (e.g., continuous RF wake for >30 seconds), the device can enter a low-power safe mode. However, this detection mechanism itself can be attacked: the attacker can time the flood to coincide with legitimate communication, masking the attack within normal power consumption.

## 8. BLE as Secondary Channel

### 8.1 BLE in Neurostimulators

Some modern neurostimulators add BLE (Bluetooth Low Energy) as a secondary communication channel, typically for home monitoring (transmitting therapy efficacy data, battery status, and device diagnostics to a smartphone app). The MICS channel remains the primary channel for clinical programming.

**BLE advantages for neurostimulators:**
- Ubiquitous hardware: smartphones, tablets, and laptops all have BLE.
- Standardized security: BLE 4.2+ includes AES-CCM encryption and public-key pairing.
- Higher bandwidth: up to 2 Mbps enables richer telemetry.
- Lower cost: no need for a custom MICS programmer.

**BLE security for neurostimulators:**
- BLE uses AES-CCM with 128-bit keys (LE Secure Connections in BLE 4.2+).
- Pairing uses ECDH for key exchange (providing forward secrecy in Secure Connections mode).
- The pairing process is well-studied and has known vulnerabilities that have been addressed in newer specifications.

### 8.2 BLE-Specific Attack Vectors

1. **BLE spoofing:** BLE advertising packets are unauthenticated. An attacker can advertise as the neurostimulator and lure the patient's smartphone into connecting to the attacker's device instead of the real implant. This is a social engineering attack combined with a protocol attack.

2. **BLE pairing downgrade:** An attacker can force a BLE connection to use a weaker pairing method (e.g., Legacy Pairing with a 6-digit PIN instead of Secure Connections with public-key crypto). The downgrade is possible if the attacker can intercept and modify the pairing request during the connection establishment.

3. **BLE tracking:** The implant's BLE advertising packets may contain a unique device identifier. An attacker who records these identifiers can track the patient's location (the implant broadcasts the identifier continuously). This is a privacy attack, not a safety attack, but it is relevant to the overall threat model.

### 8.3 Dual-Channel Security Implications

Having two communication channels (MICS + BLE) doubles the attack surface:

- **Cross-channel attacks:** An attacker who compromises one channel may be able to affect the other. For example, if the MICS and BLE channels share the same pairing key or session key, compromising one channel compromises the other.
- **Channel confusion:** The patient's smartphone (BLE channel) and the clinic's programmer (MICS channel) may send conflicting commands. The firmware must resolve conflicts (typically MICS has priority, but this must be explicitly implemented).
- **Increased firmware complexity:** Supporting two protocol stacks increases firmware size and complexity, potentially introducing more vulnerabilities.

**VIREON validation:** When a device has multiple wireless channels, VIREON should test each channel independently AND test for cross-channel attacks.