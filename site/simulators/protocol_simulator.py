"""
VIREON-LABS NL-004 Lab 001: Wireless Protocol Simulator
=====================================================

Simulates a complete MICS-band wireless protocol for neurostimulators with
security instrumentation: session establishment, authenticated encryption,
replay detection, per-command authorization, battery drain tracking, and
packet capture export.

Learning Objectives:
    1. Implement a complete implant wireless protocol stack (5 layers)
    2. Understand session establishment, challenge-response, and key derivation
    3. Observe replay detection via sliding window sequence numbers
    4. Measure protocol overhead (auth tags, nonces, headers) vs bandwidth
    5. Track battery energy consumption per packet type and state transition
    6. Compare secure vs vulnerable protocol configurations
    7. Generate packet captures for Lab 002 attack analysis

Run Modes:
    --mode demo          Full session walkthrough with annotated output
    --mode session       Extended session with command exchange and metrics
    --mode attack_test   Deliberately vulnerable mode for Lab 002 testing

Usage:
    python protocol_simulator.py --mode demo
    python protocol_simulator.py --mode session --num_commands 20
    python protocol_simulator.py --mode attack_test
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import secrets
import struct
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ============================================================================
# SECTION 1: Cryptographic Engine (Simulated AES-128-CCM)
# ============================================================================
# Real implants use hardware AES on Cortex-M4 (~0.5 us/block, ~0.05 uJ/block).
# We simulate the SECURITY PROPERTIES using HMAC-SHA256 + XOR cipher.
# The security analysis (nonce uniqueness, constant-time comparison, AEAD
# usage) is the same regardless of implementation.

class CryptoEngine:
    """Simulated authenticated encryption matching AES-128-CCM properties.
    
    Security Properties Preserved:
        - Confidentiality: payload XORed with derived keystream
        - Integrity: 8-byte authentication tag via HMAC-SHA256
        - Constant-time tag comparison via hmac.compare_digest()
        - Nonce uniqueness is caller's responsibility (same as real AES-CCM)
    
    VIREON Note:
        In production VIREON providers, this is replaced by calls to the
        device's hardware AES-CCM implementation or a validated software
        library (mbedTLS, TinyCrypt).
    """

    @staticmethod
    def derive_key(psk: bytes, nonce: bytes, context: str) -> bytes:
        """HKDF-like key derivation: KDF(psk, nonce, context) -> 16-byte key."""
        prk = hmac.new(psk, nonce + context.encode(), hashlib.sha256).digest()
        return hmac.new(prk, b'VIREON-key-expansion', hashlib.sha256).digest()[:16]

    @staticmethod
    def encrypt(key: bytes, nonce: bytes, plaintext: bytes,
                aad: bytes) -> tuple[bytes, bytes]:
        """AEAD encrypt: returns (ciphertext, 8-byte auth tag).
        
        Simulated AEAD: HMAC over ciphertext+AAD for integrity,
        XOR with derived keystream for confidentiality.
        """
        # Derive keystream and encrypt
        keystream = hashlib.sha256(key + nonce).digest()
        ct = bytes(a ^ keystream[i % len(keystream)] for i, a in enumerate(plaintext))
        # Auth tag computed over ciphertext + aad (matches decrypt verification)
        tag = hmac.new(key, nonce + aad + ct, hashlib.sha256).digest()[:8]
        return ct, tag

    @staticmethod
    def decrypt(key: bytes, nonce: bytes, ciphertext: bytes,
                aad: bytes, tag: bytes) -> Optional[bytes]:
        """AEAD decrypt: returns plaintext or None if auth fails.
        
        Uses constant-time comparison (hmac.compare_digest) to prevent
        timing side-channels on the authentication tag.
        """
        expected_tag = hmac.new(
            key, nonce + aad + ciphertext, hashlib.sha256
        ).digest()[:8]
        if not hmac.compare_digest(tag, expected_tag):
            return None
        keystream = hashlib.sha256(key + nonce).digest()
        pt = bytes(a ^ keystream[i % len(keystream)] for i, a in enumerate(ciphertext))
        return pt


# ============================================================================
# SECTION 2: Protocol Constants and Command Definitions
# ============================================================================

class PacketType(Enum):
    SESSION_REQ = 0
    CHALLENGE = 1
    AUTH_RESPONSE = 2
    SESSION_CONFIRM = 3
    DATA = 4
    ACK = 5
    SESSION_END = 6
    ERROR = 7
    KEEPALIVE = 8


class AuthLevel(Enum):
    EMERGENCY = 0    # Physical proximity only
    HOME = 1         # Patient smartphone (BLE pairing)
    CLINICAL = 2     # Clinic programmer (MICS + clinician auth)
    FIRMWARE = 3     # Manufacturer signed firmware


class ResponseCode(Enum):
    SUCCESS = 0x00
    INVALID_COMMAND = 0x01
    UNAUTHORIZED = 0x02
    PARAM_OUT_OF_RANGE = 0x03
    DEVICE_BUSY = 0x04
    SAFETY_VIOLATION = 0x05
    CRYPTO_ERROR = 0x06
    UNKNOWN = 0x07


# Command definitions from NL-004 Section 11.1
COMMANDS = {
    0x01: {"name": "GET_STATUS",       "auth": AuthLevel.HOME,     "impact": "Info disclosure"},
    0x02: {"name": "GET_IMPEDANCE",    "auth": AuthLevel.HOME,     "impact": "Info disclosure"},
    0x03: {"name": "GET_DIAGNOSTICS",  "auth": AuthLevel.CLINICAL, "impact": "Device info"},
    0x04: {"name": "SET_AMPLITUDE",    "auth": AuthLevel.CLINICAL, "impact": "Unsafe stimulation"},
    0x05: {"name": "SET_FREQUENCY",    "auth": AuthLevel.CLINICAL, "impact": "Unsafe stimulation"},
    0x06: {"name": "SET_PULSE_WIDTH",  "auth": AuthLevel.CLINICAL, "impact": "Unsafe stimulation"},
    0x07: {"name": "SET_ELECTRODE",    "auth": AuthLevel.CLINICAL, "impact": "Wrong site"},
    0x08: {"name": "START_THERAPY",   "auth": AuthLevel.CLINICAL, "impact": "Unwanted stim"},
    0x09: {"name": "STOP_THERAPY",    "auth": AuthLevel.CLINICAL, "impact": "Therapy halt"},
    0x0A: {"name": "SET_CL_PARAMS",    "auth": AuthLevel.CLINICAL, "impact": "Controller manip"},
    0x0B: {"name": "GET_NEURAL_DATA",  "auth": AuthLevel.CLINICAL, "impact": "Data exfiltration"},
    0x0C: {"name": "OTA_UPDATE",       "auth": AuthLevel.FIRMWARE,  "impact": "Firmware compromise"},
    0x0D: {"name": "PAIRING_REQUEST",  "auth": AuthLevel.CLINICAL, "impact": "New pairing"},
    0x0E: {"name": "SESSION_END",      "auth": AuthLevel.HOME,     "impact": "Session end"},
    0x0F: {"name": "EMERGENCY_STOP",   "auth": AuthLevel.EMERGENCY, "impact": "Immediate halt"},
}


# ============================================================================
# SECTION 3: Protocol State Machine
# ============================================================================

class ProtoState(Enum):
    SLEEP = auto()
    IDLE = auto()
    AUTH = auto()
    ACTIVE = auto()


class SecurityEventType(Enum):
    SESSION_INIT = auto()
    AUTH_SUCCESS = auto()
    AUTH_FAIL = auto()
    REPLAY_DETECTED = auto()
    COMMAND_RECEIVED = auto()
    COMMAND_REJECTED_AUTH = auto()
    COMMAND_REJECTED_SAFETY = auto()
    DECRYPT_FAIL = auto()
    SESSION_END = auto()
    BATTERY_DRAIN_ALERT = auto()
    STATE_TRANSITION = auto()
    SEQUENCE_ERROR = auto()


# ============================================================================
# SECTION 4: Energy Model
# ============================================================================
# Based on typical Cortex-M4 + MICS transceiver power profile.
# Reference: NL-004 Section 7.4 (battery drain attack analysis)

@dataclass
class EnergyModel:
    """Tracks energy consumption for battery drain analysis (WP-007).
    
    Energy values in microjoules (uJ).
    Typical implant battery: 250-500 mAh at 3.6V = 3240-6480 J.
    Target battery life: 5-10 years.
    """
    rx_energy: float = 0.0       # Energy per received packet
    tx_energy: float = 0.0       # Energy per transmitted packet
    crypto_energy: float = 0.0   # Energy for crypto operations
    state_energy: float = 0.0    # Energy for state transitions
    total_rx: float = 0.0
    total_tx: float = 0.0
    total_crypto: float = 0.0
    total_state: float = 0.0
    packet_count_rx: int = 0
    packet_count_tx: int = 0
    crypto_ops: int = 0
    state_transitions: int = 0

    # Per-packet energy costs (uJ) — realistic for MICS transceiver
    RX_COST: float = 2.5         # Receiver on + decode one packet
    TX_COST: float = 15.0        # Transmitter on + encode + send (25 uW ERP, ~600 us)
    CRYPTO_ENCRYPT: float = 0.08 # AES-128-CCM encrypt one block
    CRYPTO_DECRYPT: float = 0.08 # AES-128-CCM decrypt + verify
    CRYPTO_KDF: float = 5.0      # HKDF-SHA256 key derivation
    STATE_WAKE: float = 50.0     # SLEEP -> IDLE (RF receiver startup)
    STATE_AUTH: float = 20.0     # IDLE -> AUTH (crypto init)

    def record_rx(self, size_bytes: int = 32) -> None:
        cost = self.RX_COST + (size_bytes * 0.01)  # size-dependent
        self.total_rx += cost
        self.packet_count_rx += 1

    def record_tx(self, size_bytes: int = 32) -> None:
        cost = self.TX_COST + (size_bytes * 0.02)
        self.total_tx += cost
        self.packet_count_tx += 1

    def record_crypto(self, op_type: str = "encrypt") -> None:
        if op_type == "kdf":
            self.total_crypto += self.CRYPTO_KDF
        else:
            self.total_crypto += self.CRYPTO_ENCRYPT
        self.crypto_ops += 1

    def record_state_transition(self, from_state: str, to_state: str) -> None:
        if to_state == "IDLE":
            self.total_state += self.STATE_WAKE
        elif to_state == "AUTH":
            self.total_state += self.STATE_AUTH
        self.state_transitions += 1

    @property
    def total_energy_uj(self) -> float:
        return self.total_rx + self.total_tx + self.total_crypto + self.total_state

    @property
    def total_energy_mj(self) -> float:
        return self.total_energy_uj / 1e6

    def summary(self) -> dict:
        return {
            "total_energy_uj": round(self.total_energy_uj, 2),
            "total_energy_mj": round(self.total_energy_mj, 6),
            "rx_packets": self.packet_count_rx,
            "tx_packets": self.packet_count_tx,
            "crypto_ops": self.crypto_ops,
            "state_transitions": self.state_transitions,
            "rx_energy_uj": round(self.total_rx, 2),
            "tx_energy_uj": round(self.total_tx, 2),
            "crypto_energy_uj": round(self.total_crypto, 2),
            "state_energy_uj": round(self.total_state, 2),
        }


# ============================================================================
# SECTION 5: Packet Structure
# ============================================================================
# Format from NL-004 Section 3.1:
# | Preamble (1B: 0xAA) | Type (1B) | Seq (2B) | Addr (1B) | Payload (N) | AuthTag (8B) |

@dataclass
class Packet:
    """Wireless protocol packet with full security instrumentation."""
    ptype: int
    seq: int
    payload: bytes = b''
    auth_tag: bytes = b''
    device_addr: int = 0x0001
    auth_level: AuthLevel = AuthLevel.CLINICAL
    timestamp_ms: float = 0.0
    raw_bytes: bytes = b''
    nonce: bytes = b''  # Stored for packet capture export

    HEADER_SIZE = 5  # preamble(1) + type(1) + seq(2) + addr(1)
    TAG_SIZE = 8
    MIN_SIZE = HEADER_SIZE + TAG_SIZE  # 13 bytes minimum

    def encode(self) -> bytes:
        header = struct.pack('>BBH B', 0xAA, self.ptype, self.seq, self.device_addr)
        raw = header + self.payload + self.auth_tag
        self.raw_bytes = raw
        return raw

    @classmethod
    def decode(cls, data: bytes) -> Optional[Packet]:
        if len(data) < 5:
            return None
        if data[0] != 0xAA:
            return None
        ptype = data[1]
        seq = struct.unpack_from('>H', data, 2)[0]
        addr = data[4]
        # Auth tag is only present on DATA packets (ptype 4) which are encrypted
        # Other packet types (session_req, challenge, auth_response, etc.) are unencrypted
        has_tag = (ptype == PacketType.DATA.value and len(data) >= 13)
        if has_tag:
            payload = data[5:-8]
            tag = data[-8:]
        else:
            payload = data[5:]
            tag = b''
        pkt = cls(ptype=ptype, seq=seq, payload=payload, auth_tag=tag,
                  device_addr=addr)
        pkt.raw_bytes = data
        return pkt

    @property
    def overhead_bytes(self) -> int:
        """Security and framing overhead vs payload-only transmission."""
        return self.HEADER_SIZE + len(self.auth_tag)

    @property
    def overhead_ratio(self) -> float:
        payload_len = max(len(self.payload), 1)
        return self.overhead_bytes / payload_len

    def summary(self) -> dict:
        return {
            "ptype": self.ptype,
            "ptype_name": PacketType(self.ptype).name if self.ptype < 9 else "UNKNOWN",
            "seq": self.seq,
            "device_addr": hex(self.device_addr),
            "payload_size": len(self.payload),
            "has_auth_tag": len(self.auth_tag) == 8,
            "total_size": len(self.raw_bytes) if self.raw_bytes else self.HEADER_SIZE + len(self.payload) + len(self.auth_tag),
            "overhead_bytes": self.overhead_bytes,
            "overhead_ratio": round(self.overhead_ratio, 3),
        }


# ============================================================================
# SECTION 6: Implant Protocol Implementation
# ============================================================================

class ImplantProtocol:
    """Simulated implant-side MICS protocol with full security stack.
    
    VIREON Integration:
        This class models the implant's protocol behavior for:
        - Digital twin wireless channel simulation
        - Protocol analyzer provider testing
        - WP-001 through WP-008 benchmark execution
    
    Security Features:
        - Challenge-response session establishment
        - AES-CCM (simulated) for data packets
        - Sliding window replay detection (configurable window)
        - Per-command authorization (4 levels)
        - Battery energy tracking per operation
        - Security event logging for VIREON analysis
    
    Vulnerable Mode (--mode attack_test):
        When vulnerable=True, the following weaknesses are introduced:
        1. Auth tag is not verified on data packets (tag check skipped)
        2. Sequence window is widened to 65535 (replay accepted)
        3. Authorization is per-session, not per-command (any cmd accepted)
        4. No battery drain detection (energy not monitored)
        These map to real-world vulnerabilities in legacy devices.
    """

    def __init__(self, device_addr: int = 0x0001, psk: Optional[bytes] = None,
                 auth_window: int = 16, vulnerable: bool = False,
                 session_auth_level: AuthLevel = AuthLevel.CLINICAL) -> None:
        self.device_addr = device_addr
        self.psk = psk or hashlib.sha256(b'VIREON-implant-PSK-v1').digest()[:16]
        self.vulnerable = vulnerable
        self.session_auth_level = session_auth_level
        
        # State machine
        self.state = ProtoState.SLEEP
        self.prev_state = ProtoState.SLEEP
        
        # Session parameters
        self.session_key: Optional[bytes] = None
        self.session_id = 0
        self.challenge: Optional[bytes] = None
        self.auth_window = auth_window
        
        # Sequence number management (NL-004 Section 6.3)
        self.tx_seq = 0
        self.rx_window_max = 0
        self.rx_seen: set[int] = set()  # Track seen seqs for within-session replay
        
        # Nonce management
        self.nonce_counter = 0
        self.boot_nonce = secrets.randbits(32)  # Prevents nonce reuse after reboot
        
        # Security logging
        self.log: list[dict] = []
        self.packet_record: list[dict] = []
        
        # Energy tracking
        self.energy = EnergyModel()
        
        # Protocol metrics
        self.commands_executed: list[dict] = []
        self.session_start_time: Optional[float] = None

    def _log_event(self, event_type: SecurityEventType,
                   details: dict = None) -> None:
        entry = {
            "time_ms": round(time.time() * 1000, 2),
            "event": event_type.name,
            "state": self.state.name,
            "session_id": self.session_id,
            "vulnerable_mode": self.vulnerable,
            "details": details or {},
        }
        self.log.append(entry)

    def _transition(self, new_state: ProtoState) -> None:
        self.prev_state = self.state
        self.state = new_state
        self._log_event(SecurityEventType.STATE_TRANSITION, {
            "from": self.prev_state.name,
            "to": new_state.name,
        })
        self.energy.record_state_transition(self.prev_state.name, new_state.name)

    def _make_nonce(self) -> bytes:
        """Generate unique 12-byte nonce.
        
        Format: device_addr(2B) | session_id(4B) | boot_nonce(4B) | pkt_counter(2B)
        The boot_nonce prevents nonce reuse after device reset.
        """
        self.nonce_counter += 1
        return struct.pack('>H I I H',
                           self.device_addr, self.session_id,
                           self.boot_nonce, self.nonce_counter & 0xFFFF)

    def _make_packet(self, ptype: int, payload: bytes,
                     encrypt: bool = False) -> Packet:
        pkt = Packet(ptype=ptype, seq=self.tx_seq, payload=payload,
                     device_addr=self.device_addr)
        pkt.timestamp_ms = time.time() * 1000
        
        if encrypt and self.session_key:
            nonce = self._make_nonce()
            aad = struct.pack('>BBH B', 0xAA, ptype, self.tx_seq, self.device_addr)
            ct, tag = CryptoEngine.encrypt(self.session_key, nonce, payload, aad)
            pkt.payload = ct
            pkt.auth_tag = tag
            pkt.nonce = nonce
            self.energy.record_crypto("encrypt")
        
        self.tx_seq = (self.tx_seq + 1) & 0xFFFF
        return pkt

    def _check_seq(self, seq: int) -> bool:
        """Sliding window replay detection (NL-004 Section 6.3).
        
        In vulnerable mode: window is effectively infinite (65535),
        allowing replay of any packet.
        """
        if self.vulnerable:
            return True  # VULNERABILITY: No replay protection
        
        # Reject packets below the window
        if seq < self.rx_window_max - self.auth_window and \
           self.rx_window_max > self.auth_window:
            self._log_event(SecurityEventType.SEQUENCE_ERROR, {
                "pkt_seq": seq, "window_max": self.rx_window_max,
                "window_min": self.rx_window_max - self.auth_window,
                "reason": "below_window",
            })
            return False
        
        # Check for within-session duplicate (exact seq already seen)
        if seq in self.rx_seen:
            self._log_event(SecurityEventType.REPLAY_DETECTED, {
                "pkt_seq": seq, "reason": "duplicate_in_window",
            })
            return False
        
        # Advance window if new highest
        if seq > self.rx_window_max:
            # Prune old entries from seen set
            old_min = self.rx_window_max - self.auth_window
            self.rx_seen = {s for s in self.rx_seen if s >= seq - self.auth_window}
            self.rx_window_max = seq
        
        self.rx_seen.add(seq)
        return True

    def _make_rx_nonce(self, pkt_seq: int) -> bytes:
        """Reconstruct the nonce the sender used for this packet.
        
        Both sides derive nonce from the same formula:
        device_addr(2B) | session_id(4B) | boot_nonce(4B) | pkt_counter(2B)
        The pkt_counter for RX is the received packet's sequence number.
        This ensures programmer's encrypt nonce matches implant's decrypt nonce.
        """
        return struct.pack('>H I I H',
                           self.device_addr, self.session_id,
                           self.boot_nonce, pkt_seq & 0xFFFF)

    def _check_authorization(self, cmd_id: int) -> bool:
        """Per-command authorization check (NL-004 Section 11.2).
        
        In vulnerable mode: authorization is per-session only.
        All commands are accepted if session is authenticated.
        This maps to the Medtronic insulin pump vulnerability pattern.
        """
        if self.vulnerable:
            return True  # VULNERABILITY: No per-command authorization
        
        if cmd_id not in COMMANDS:
            return False
        
        required = COMMANDS[cmd_id]["auth"]
        return self.session_auth_level.value >= required.value

    def process_packet(self, raw: bytes) -> Optional[Packet]:
        """Process a received packet through the full protocol stack.
        
        Pipeline (NL-004 Section 1.3):
            1. Physical: decode packet from raw bytes
            2. MAC: check minimum size
            3. Transport: check sequence number (replay detection)
            4. Security: verify authentication tag, decrypt
            5. Application: check authorization, execute command
        """
        self.energy.record_rx(len(raw))
        
        # Layer 1+2: Packet decode
        pkt = Packet.decode(raw)
        if pkt is None:
            self._log_event(SecurityEventType.COMMAND_REJECTED_AUTH, {
                "reason": "invalid_packet_format", "raw_size": len(raw),
            })
            return None

        # Record for packet capture
        record = {
            "dir": "rx", "ptype": pkt.ptype,
            "ptype_name": PacketType(pkt.ptype).name if pkt.ptype < 9 else "UNKNOWN",
            "seq": pkt.seq, "size": len(raw),
            "has_auth_tag": len(pkt.auth_tag) == 8,
            "device_addr": hex(pkt.device_addr),
            "timestamp_ms": pkt.timestamp_ms,
        }
        self.packet_record.append(record)

        # ---- State Machine Dispatch ----
        
        if self.state == ProtoState.SLEEP:
            if pkt.ptype == PacketType.SESSION_REQ.value:
                self._transition(ProtoState.IDLE)
                self._transition(ProtoState.AUTH)
                self.session_id += 1
                self.challenge = secrets.token_bytes(16)
                self._log_event(SecurityEventType.SESSION_INIT, {
                    "session_id": self.session_id,
                    "challenge_preview": self.challenge[:8].hex(),
                })
                resp = self._make_packet(PacketType.CHALLENGE.value, self.challenge)
                self.energy.record_tx(len(resp.encode()))
                return resp
            return None

        elif self.state == ProtoState.AUTH:
            if pkt.ptype == PacketType.AUTH_RESPONSE.value and self.challenge:
                # Verify HMAC proof of knowledge
                expected = hmac.new(
                    self.psk, self.challenge, hashlib.sha256
                ).digest()[:16]
                
                if hmac.compare_digest(pkt.payload, expected):
                    # Auth success — derive session key
                    self.session_key = CryptoEngine.derive_key(
                        self.psk, self.challenge,
                        f"VIREON-session-{self.session_id}"
                    )
                    self.energy.record_crypto("kdf")
                    self.tx_seq = 0
                    self.rx_window_max = 0
                    self.rx_seen.clear()
                    self.nonce_counter = 0
                    self.session_start_time = time.time()
                    self._transition(ProtoState.ACTIVE)
                    self._log_event(SecurityEventType.AUTH_SUCCESS, {
                        "session_id": self.session_id,
                    })
                    resp = self._make_packet(
                        PacketType.SESSION_CONFIRM.value, b'SESSION_OK'
                    )
                    self.energy.record_tx(len(resp.encode()))
                    return resp
                else:
                    self._log_event(SecurityEventType.AUTH_FAIL, {
                        "session_id": self.session_id,
                        "reason": "invalid_proof",
                    })
                    self._transition(ProtoState.IDLE)
                    resp = Packet(ptype=PacketType.ERROR.value, seq=0,
                                  payload=struct.pack('B', ResponseCode.CRYPTO_ERROR.value))
                    self.energy.record_tx(len(resp.encode()))
                    return resp
            return None

        elif self.state == ProtoState.ACTIVE:
            # Layer 3: Replay detection
            if not self._check_seq(pkt.seq):
                resp = Packet(ptype=PacketType.ERROR.value, seq=0,
                              payload=struct.pack('B', ResponseCode.UNKNOWN.value))
                self.energy.record_tx(len(resp.encode()))
                return resp

            # Session end
            if pkt.ptype == PacketType.SESSION_END.value:
                duration = 0
                if self.session_start_time:
                    duration = time.time() - self.session_start_time
                self._log_event(SecurityEventType.SESSION_END, {
                    "session_id": self.session_id,
                    "duration_s": round(duration, 3),
                    "energy_uj": self.energy.total_energy_uj,
                })
                self._transition(ProtoState.IDLE)
                self.session_key = None
                resp = Packet(ptype=PacketType.ACK.value, seq=0,
                              payload=b'BYE')
                self.energy.record_tx(len(resp.encode()))
                return resp

            # Data packet (command)
            if pkt.ptype == PacketType.DATA.value:
                # Layer 4: Security verification
                if self.session_key and len(pkt.auth_tag) == 8:
                    nonce = self._make_rx_nonce(pkt.seq)
                    aad = struct.pack('>BBH B', 0xAA, pkt.ptype, pkt.seq,
                                       pkt.device_addr)
                    
                    # VULNERABILITY: In attack_test mode, skip auth tag verify
                    # but still decrypt so command IDs are readable (real devices do decrypt,
                    # they just don't verify the tag — the actual vulnerability)
                    if self.vulnerable:
                        # Decrypt without tag verification
                        keystream = hashlib.sha256(self.session_key + nonce).digest()
                        pt = bytes(a ^ keystream[i % len(keystream)] for i, a in enumerate(pkt.payload))
                    else:
                        pt = CryptoEngine.decrypt(
                            self.session_key, nonce, pkt.payload,
                            aad, pkt.auth_tag
                        )
                        self.energy.record_crypto("decrypt")
                else:
                    pt = None

                if pt is None:
                    self._log_event(SecurityEventType.DECRYPT_FAIL, {
                        "seq": pkt.seq,
                        "has_key": self.session_key is not None,
                        "tag_len": len(pkt.auth_tag),
                    })
                    resp = Packet(ptype=PacketType.ERROR.value, seq=0,
                                  payload=struct.pack('B', ResponseCode.CRYPTO_ERROR.value))
                    self.energy.record_tx(len(resp.encode()))
                    return resp

                # Layer 5: Application — parse and authorize command
                if len(pt) < 1:
                    self._log_event(SecurityEventType.COMMAND_REJECTED_AUTH, {
                        "reason": "empty_payload", "seq": pkt.seq,
                    })
                    resp = Packet(ptype=PacketType.ERROR.value, seq=0,
                                  payload=struct.pack('B', ResponseCode.INVALID_COMMAND.value))
                    self.energy.record_tx(len(resp.encode()))
                    return resp

                cmd_id = pt[0]
                cmd_params = pt[1:] if len(pt) > 1 else b''

                # Authorization check
                if not self._check_authorization(cmd_id):
                    self._log_event(SecurityEventType.COMMAND_REJECTED_AUTH, {
                        "cmd_id": hex(cmd_id),
                        "cmd_name": COMMANDS.get(cmd_id, {}).get("name", "UNKNOWN"),
                        "required_auth": COMMANDS.get(cmd_id, {}).get("auth", "?").name if cmd_id in COMMANDS else "?",
                        "session_auth": self.session_auth_level.name,
                        "reason": "insufficient_authorization",
                    })
                    resp = Packet(ptype=PacketType.ERROR.value, seq=0,
                                  payload=struct.pack('B', ResponseCode.UNAUTHORIZED.value))
                    self.energy.record_tx(len(resp.encode()))
                    return resp

                cmd_name = COMMANDS.get(cmd_id, {}).get("name", f"UNKNOWN_0x{cmd_id:02X}")
                self._log_event(SecurityEventType.COMMAND_RECEIVED, {
                    "cmd_id": hex(cmd_id),
                    "cmd_name": cmd_name,
                    "seq": pkt.seq,
                    "params_size": len(cmd_params),
                    "params_preview": cmd_params[:16].hex() if cmd_params else "(none)",
                })

                self.commands_executed.append({
                    "cmd_id": cmd_id, "cmd_name": cmd_name,
                    "params": cmd_params.hex(),
                    "seq": pkt.seq, "auth_level": self.session_auth_level.name,
                })

                # Send encrypted ACK with command echo
                ack_payload = struct.pack('B', ResponseCode.SUCCESS.value) + pt
                resp = self._make_packet(PacketType.DATA.value, ack_payload, encrypt=True)
                self.energy.record_tx(len(resp.encode()))
                return resp

            # Keepalive
            if pkt.ptype == PacketType.KEEPALIVE.value:
                resp = Packet(ptype=PacketType.ACK.value, seq=0, payload=b'ALIVE')
                self.energy.record_tx(len(resp.encode()))
                return resp

        # Fallback
        self._log_event(SecurityEventType.COMMAND_REJECTED_AUTH, {
            "state": self.state.name, "ptype": pkt.ptype,
            "reason": "unhandled_in_state",
        })
        return None

    def get_session_report(self) -> dict:
        """Generate comprehensive session report for VIREON analysis."""
        duration = 0
        if self.session_start_time and self.state == ProtoState.ACTIVE:
            duration = time.time() - self.session_start_time
        return {
            "device_addr": hex(self.device_addr),
            "state": self.state.name,
            "session_id": self.session_id,
            "vulnerable_mode": self.vulnerable,
            "session_auth_level": self.session_auth_level.name,
            "duration_s": round(duration, 3),
            "energy": self.energy.summary(),
            "packets_received": len([p for p in self.packet_record if p["dir"] == "rx"]),
            "packets_sent": self.energy.packet_count_tx,
            "security_events": len(self.log),
            "auth_failures": len([e for e in self.log if e["event"] == "AUTH_FAIL"]),
            "replay_detected": len([e for e in self.log if e["event"] == "REPLAY_DETECTED"]),
            "commands_executed": len(self.commands_executed),
            "auth_rejections": len([e for e in self.log if e["event"] == "COMMAND_REJECTED_AUTH"]),
        }


# ============================================================================
# SECTION 7: Programmer Protocol Implementation
# ============================================================================

class ProgrammerProtocol:
    """Simulated programmer-side MICS protocol.
    
    Supports multiple authorization levels for testing per-command
    authorization (NL-004 Section 11.2).
    """

    def __init__(self, implant: ImplantProtocol,
                 auth_level: AuthLevel = AuthLevel.CLINICAL) -> None:
        self.implant = implant
        self.psk = implant.psk
        self.tx_seq = 0
        self.session_key: Optional[bytes] = None
        self.auth_level = auth_level

    def initiate_session(self) -> Optional[Packet]:
        # Do NOT set state here — process_packet transitions SLEEP->IDLE->AUTH
        req = Packet(ptype=PacketType.SESSION_REQ.value, seq=0,
                     device_addr=self.implant.device_addr)
        resp = self.implant.process_packet(req.encode())
        return resp

    def authenticate(self, challenge: bytes) -> Optional[Packet]:
        """Step 2: Prove knowledge of PSK via HMAC."""
        proof = hmac.new(self.psk, challenge, hashlib.sha256).digest()[:16]
        req = Packet(ptype=PacketType.AUTH_RESPONSE.value, seq=0,
                     payload=proof)
        resp = self.implant.process_packet(req.encode())
        if resp and resp.ptype == PacketType.SESSION_CONFIRM.value:
            # Derive session key
            self.session_key = CryptoEngine.derive_key(
                self.psk, challenge,
                f"VIREON-session-{self.implant.session_id}"
            )
        return resp

    def send_command(self, cmd_id: int, params: bytes = b'') -> Optional[Packet]:
        """Step 3: Send encrypted command packet.
        
        Payload format: cmd_id (1B) || params (N B)
        """
        if not self.session_key:
            return None
        payload = struct.pack('B', cmd_id) + params
        # Nonce matches implant's _make_rx_nonce: addr(2) | session(4) | boot(4) | seq(2)
        nonce = struct.pack('>H I I H',
                           self.implant.device_addr,
                           self.implant.session_id,
                           self.implant.boot_nonce,
                           self.tx_seq & 0xFFFF)
        aad = struct.pack('>BBH B', 0xAA, PacketType.DATA.value,
                           self.tx_seq, self.implant.device_addr)
        ct, tag = CryptoEngine.encrypt(self.session_key, nonce, payload, aad)
        pkt = Packet(ptype=PacketType.DATA.value, seq=self.tx_seq,
                     payload=ct, auth_tag=tag,
                     device_addr=self.implant.device_addr)
        pkt.nonce = nonce
        self.tx_seq += 1
        return self.implant.process_packet(pkt.encode())

    def end_session(self) -> Optional[Packet]:
        """Terminate the session."""
        pkt = Packet(ptype=PacketType.SESSION_END.value,
                     seq=self.tx_seq, device_addr=self.implant.device_addr)
        return self.implant.process_packet(pkt.encode())


# ============================================================================
# SECTION 8: Run Modes
# ============================================================================

def demo_mode() -> None:
    """Full protocol session walkthrough with security annotations."""
    print("=" * 70)
    print("  VIREON Protocol Simulator: Session Demo (Secure Mode)")
    print("  NL-004 Lab 001 — Learning Mode")
    print("=" * 70)

    implant = ImplantProtocol(device_addr=0x0001)
    programmer = ProgrammerProtocol(implant, auth_level=AuthLevel.CLINICAL)

    print(f"\n{'─' * 70}")
    print(f"  STEP 1: Session Establishment")
    print(f"{'─' * 70}")
    print(f"  Implant state: {implant.state.name}")
    print(f"  Initiating session request...")

    resp = programmer.initiate_session()
    if resp:
        print(f"  Implant state: {implant.state.name}")
        print(f"  Challenge received: {resp.payload.hex()}")
        print(f"  Challenge size: {len(resp.payload)} bytes (cryptographic nonce)")
        print(f"  Packet overhead: {resp.overhead_bytes}B header + {len(resp.auth_tag)}B tag = {resp.overhead_ratio:.1f}x ratio")

    print(f"\n  STEP 2: Authentication (Challenge-Response)")
    resp = programmer.authenticate(implant.challenge or b'')
    if resp:
        print(f"  Auth result: {resp.payload}")
        print(f"  Implant state: {implant.state.name}")
        print(f"  Session ID: {implant.session_id}")
        print(f"  Session key derived: {implant.session_key.hex()[:32]}..." if implant.session_key else "  Key: None")

    print(f"\n  STEP 3: Encrypted Command Exchange")
    print(f"  {'CMD':<20} {'ID':<6} {'Auth Req':<12} {'Result'}")
    print(f"  {'─' * 60}")

    test_commands = [
        (0x01, b'', "GET_STATUS"),
        (0x04, struct.pack('>f', 3.0), "SET_AMPLITUDE"),
        (0x05, struct.pack('>H', 130), "SET_FREQUENCY"),
        (0x08, b'', "START_THERAPY"),
        (0x0B, b'', "GET_NEURAL_DATA"),
    ]

    for cmd_id, params, name in test_commands:
        auth_req = COMMANDS[cmd_id]["auth"].name
        resp = programmer.send_command(cmd_id, params)
        status = "OK" if resp and resp.ptype == PacketType.DATA.value else "FAIL"
        print(f"  {name:<20} 0x{cmd_id:02X}  {auth_req:<12} {status}")

    print(f"\n  STEP 4: Session Termination")
    resp = programmer.end_session()
    if resp:
        print(f"  Result: {resp.payload}")
        print(f"  Implant state: {implant.state.name}")

    report = implant.get_session_report()
    print(f"\n{'─' * 70}")
    print(f"  SESSION REPORT")
    print(f"{'─' * 70}")
    print(f"  Total packets RX:       {report['packets_received']}")
    print(f"  Total packets TX:       {report['packets_sent']}")
    print(f"  Commands executed:      {report['commands_executed']}")
    print(f"  Security events:       {report['security_events']}")
    print(f"  Replay detections:     {report['replay_detected']}")
    print(f"  Auth rejections:       {report['auth_rejections']}")
    print(f"  Total energy:          {report['energy']['total_energy_uj']:.1f} uJ")
    print(f"    RX energy:           {report['energy']['rx_energy_uj']:.1f} uJ")
    print(f"    TX energy:           {report['energy']['tx_energy_uj']:.1f} uJ")
    print(f"    Crypto energy:       {report['energy']['crypto_energy_uj']:.1f} uJ")
    print(f"    State transition:    {report['energy']['state_energy_uj']:.1f} uJ")

    # Export
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
    export = {
        "mode": "demo",
        "session_report": report,
        "security_log": implant.log,
        "packet_record": implant.packet_record,
        "commands_executed": implant.commands_executed,
        "energy_detail": implant.energy.summary(),
    }
    out_path = os.path.join(out_dir, "protocol_session.json")
    with open(out_path, 'w') as f:
        json.dump(export, f, indent=2, default=str)
    print(f"\n  Session exported: {out_path}")


def session_mode(num_commands: int = 20) -> None:
    """Extended session for protocol metrics and packet capture generation."""
    print("=" * 70)
    print(f"  VIREON Protocol Simulator: Extended Session ({num_commands} commands)")
    print("  Generates packet capture for Lab 002 analysis")
    print("=" * 70)

    implant = ImplantProtocol(device_addr=0x0001)
    programmer = ProgrammerProtocol(implant, auth_level=AuthLevel.CLINICAL)

    # Establish session
    resp = programmer.initiate_session()
    if not resp or resp.ptype != PacketType.CHALLENGE.value:
        print("ERROR: Session initiation failed")
        return
    print(f"  Session {implant.session_id} initiated.")

    resp = programmer.authenticate(implant.challenge or b'')
    if not resp or resp.ptype != PacketType.SESSION_CONFIRM.value:
        print("ERROR: Authentication failed")
        return
    print(f"  Authenticated. Sending {num_commands} commands...")

    # Send mix of commands
    command_sequence = [
        0x01, 0x04, 0x05, 0x06, 0x07, 0x08,  # Setup
        0x01, 0x01, 0x01,                       # Telemetry
        0x0B, 0x03,                             # Diagnostics
        0x04, 0x05,                             # Adjust
        0x01, 0x01,                             # Monitor
        0x0A,                                   # CL params
    ]
    
    # Extend if needed
    while len(command_sequence) < num_commands:
        command_sequence.extend([0x01, 0x04, 0x05])
    command_sequence = command_sequence[:num_commands]

    for i, cmd_id in enumerate(command_sequence):
        params = b''
        if cmd_id == 0x04:
            params = struct.pack('>f', 2.0 + (i % 5) * 0.5)
        elif cmd_id == 0x05:
            params = struct.pack('>H', 130 + (i % 3) * 10)
        programmer.send_command(cmd_id, params)

    programmer.end_session()

    report = implant.get_session_report()
    print(f"\n  Session complete.")
    print(f"  Commands executed: {report['commands_executed']}")
    print(f"  Total energy: {report['energy']['total_energy_uj']:.1f} uJ")
    print(f"  Avg energy/cmd: {report['energy']['total_energy_uj'] / max(report['commands_executed'], 1):.1f} uJ")

    # Export packet capture for Lab 002
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
    export = {
        "mode": "session",
        "session_report": report,
        "security_log": implant.log,
        "packet_record": implant.packet_record,
        "commands_executed": implant.commands_executed,
        "session_key_hex": implant.session_key.hex() if implant.session_key else None,
        "psk_hex": implant.psk.hex(),
        "device_addr": hex(implant.device_addr),
        "session_id": implant.session_id,
        "boot_nonce": implant.boot_nonce,
        "challenge_hex": implant.challenge.hex() if implant.challenge else None,
    }
    out_path = os.path.join(out_dir, "packet_capture.json")
    with open(out_path, 'w') as f:
        json.dump(export, f, indent=2, default=str)
    print(f"  Packet capture exported: {out_path}")
    print(f"  (Lab 002 will use this for attack simulation)")


def attack_test_mode() -> None:
    """Vulnerable mode for Lab 002 attack testing.
    
    Intentional vulnerabilities:
    1. No auth tag verification (accepts any tag)
    2. No replay protection (infinite window)
    3. No per-command authorization (session-level only)
    4. No battery drain detection
    
    These map to real-world device vulnerabilities.
    """
    print("=" * 70)
    print("  VIREON Protocol Simulator: ATTACK TEST MODE")
    print("  *** VULNERABLE CONFIGURATION — For Lab 002 testing only ***")
    print("=" * 70)
    print("  Vulnerabilities enabled:")
    print("    1. Auth tag verification: DISABLED")
    print("    2. Replay protection:      DISABLED")
    print("    3. Per-command auth:        DISABLED")
    print("    4. Battery drain detection: DISABLED")

    implant = ImplantProtocol(device_addr=0x0001, vulnerable=True,
                               session_auth_level=AuthLevel.HOME)  # Low-priv session
    programmer = ProgrammerProtocol(implant, auth_level=AuthLevel.HOME)

    print(f"\n  Session auth level: HOME (lowest privilege)")
    print(f"  In secure mode, only GET_STATUS, GET_IMPEDANCE, SESSION_END allowed.")
    print(f"  In vulnerable mode, ALL commands accepted (VULNERABILITY 3).")

    # Establish session
    resp = programmer.initiate_session()
    if not resp:
        print("  ERROR: Session initiation failed")
        return
    print(f"\n  Session {implant.session_id} initiated.")

    resp = programmer.authenticate(implant.challenge or b'')
    if not resp:
        print("  ERROR: Authentication failed")
        return
    print(f"  Authenticated (HOME level).")

    # Attempt clinical commands in HOME session
    print(f"\n  Testing per-command authorization bypass:")
    print(f"  {'CMD':<20} {'ID':<6} {'Required':<12} {'Session':<10} {'Result'}")
    print(f"  {'─' * 70}")

    test_cmds = [
        (0x01, b'', "GET_STATUS", "HOME"),
        (0x04, struct.pack('>f', 7.0), "SET_AMPLITUDE", "CLINICAL"),
        (0x05, struct.pack('>H', 250), "SET_FREQUENCY", "CLINICAL"),
        (0x08, b'', "START_THERAPY", "CLINICAL"),
        (0x0C, b'', "OTA_UPDATE", "FIRMWARE"),
    ]

    for cmd_id, params, name, req_auth in test_cmds:
        resp = programmer.send_command(cmd_id, params)
        if resp and resp.ptype == PacketType.DATA.value:
            status = "ACCEPTED (VULN!)" if req_auth != "HOME" else "ACCEPTED (OK)"
        elif resp and resp.ptype == PacketType.ERROR.value:
            rc = resp.payload[0] if resp.payload else 0
            status = f"REJECTED ({ResponseCode(rc).name})"
        else:
            status = "NO RESPONSE"
        print(f"  {name:<20} 0x{cmd_id:02X}  {req_auth:<12} HOME       {status}")

    # Test replay: send same command twice
    print(f"\n  Testing replay protection:")
    resp1 = programmer.send_command(0x01, b'')
    resp2 = programmer.send_command(0x01, b'')
    print(f"  First GET_STATUS:   {'OK' if resp1 else 'FAIL'}")
    print(f"  Second GET_STATUS:  {'ACCEPTED (VULN!)' if resp2 and resp2.ptype == PacketType.DATA.value else 'REJECTED'}")
    print(f"  (In secure mode, duplicate seq would be detected)")

    programmer.end_session()

    # Export
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
    export = {
        "mode": "attack_test",
        "session_report": implant.get_session_report(),
        "security_log": implant.log,
        "packet_record": implant.packet_record,
        "commands_executed": implant.commands_executed,
        "vulnerabilities": [
            "no_auth_tag_verify",
            "no_replay_protection",
            "no_per_command_auth",
            "no_battery_detection",
        ],
    }
    out_path = os.path.join(out_dir, "vulnerable_session.json")
    with open(out_path, 'w') as f:
        json.dump(export, f, indent=2, default=str)
    print(f"\n  Vulnerable session exported: {out_path}")
    print(f"  (Lab 002 will exploit these vulnerabilities)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="VIREON Protocol Simulator (NL-004 Lab 001)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python protocol_simulator.py --mode demo
  python protocol_simulator.py --mode session --num_commands 30
  python protocol_simulator.py --mode attack_test
""")
    parser.add_argument("--mode", choices=["demo", "session", "attack_test"],
                        default="demo",
                        help="Run mode: demo (annotated walkthrough), "
                             "session (extended metrics), "
                             "attack_test (vulnerable configuration)")
    parser.add_argument("--num_commands", type=int, default=20,
                        help="Number of commands in session mode (default: 20)")
    parser.add_argument("--output_dir", type=str, default=None,
                        help="Override output directory")
    args = parser.parse_args()

    if args.mode == "demo":
        demo_mode()
    elif args.mode == "session":
        session_mode(args.num_commands)
    elif args.mode == "attack_test":
        attack_test_mode()


if __name__ == "__main__":
    main()
