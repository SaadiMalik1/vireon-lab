"""
VIREON-LABS NL-004 Lab 001: Wireless Protocol Simulator
=====================================================

Simulates a MICS-band wireless protocol for neurostimulators with
security instrumentation: session establishment, AES-CCM encryption,
replay detection, and per-command authorization.

Learning Objectives:
    1. Implement a complete implant wireless protocol
    2. Understand session establishment and key derivation
    3. Observe replay detection in action
    4. Measure protocol overhead and security trade-offs
    5. Generate packet captures for Lab 002 attack analysis

Usage:
    python protocol_simulator.py --mode demo
    python protocol_simulator.py --mode session
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import struct
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

# Simplified AES-CCM using HMAC-SHA256 for simulation
# (Real devices use hardware AES — this simulates the behavior)

class CryptoEngine:
    """Simplified authenticated encryption simulation.
    
    Security Note:
        In a real device, this is AES-128-CCM in hardware.
        We use HMAC-SHA256 + XOR cipher to simulate the
        confidentiality and integrity properties.
    """
    @staticmethod
    def derive_key(psk: bytes, nonce: bytes, context: str) -> bytes:
        return hashlib.sha256(psk + nonce + context.encode()).digest()[:16]

    @staticmethod
    def encrypt(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> tuple[bytes, bytes]:
        # Simulated AEAD: HMAC for auth, XOR for "encryption"
        tag = hmac.new(key, nonce + aad + plaintext, hashlib.sha256).digest()[:8]
        keystream = hashlib.sha256(key + nonce).digest()
        ct = bytes(a ^ keystream[i % len(keystream)] for i, a in enumerate(plaintext))
        return ct, tag

    @staticmethod
    def decrypt(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes, tag: bytes) -> Optional[bytes]:
        expected_tag = hmac.new(key, nonce + aad + ciphertext, hashlib.sha256).digest()[:8]
        if not hmac.compare_digest(tag, expected_tag):
            return None
        keystream = hashlib.sha256(key + nonce).digest()
        pt = bytes(a ^ keystream[i % len(keystream)] for i, a in enumerate(ciphertext))
        return pt


class ProtoState(Enum):
    SLEEP = auto()
    IDLE = auto()
    AUTH = auto()
    ACTIVE = auto()


@dataclass
class Packet:
    ptype: int      # 0=session_req, 1=challenge, 2=response, 3=session_confirm, 4=data, 5=ack, 6=session_end
    seq: int
    payload: bytes = b''
    auth_tag: bytes = b''
    device_addr: int = 0x0001

    def encode(self) -> bytes:
        header = struct.pack('>BBH B', 0xAA, self.ptype, self.seq, self.device_addr)
        return header + self.payload + self.auth_tag

    @classmethod
    def decode(cls, data: bytes) -> Optional['Packet']:
        if len(data) < 7:
            return None
        if data[0] != 0xAA:
            return None
        ptype = data[1]
        seq = struct.unpack_from('>H', data, 2)[0]
        addr = data[4]
        payload = data[5:-8] if len(data) > 13 else data[5:]
        tag = data[-8:] if len(data) >= 13 else b'\x00' * 8
        return cls(ptype=ptype, seq=seq, payload=payload, auth_tag=tag, device_addr=addr)


class ImplantProtocol:
    """Simulated implant-side MICS protocol.
    
    VIREON Integration:
        This simulator models the implant's protocol behavior
        for wireless channel digital twin testing.
    """
    def __init__(self, device_addr: int = 0x0001, psk: Optional[bytes] = None,
                 auth_window: int = 16) -> None:
        self.device_addr = device_addr
        self.psk = psk or hashlib.sha256(b'VIREON-implant-key').digest()[:16]
        self.state = ProtoState.SLEEP
        self.session_key: Optional[bytes] = None
        self.session_nonce: Optional[bytes] = None
        self.tx_seq = 0
        self.rx_seq = 0
        self.auth_window = auth_window
        self.rx_window_max = 0
        self.challenge: Optional[bytes] = None
        self.session_id = 0
        self.log: list[dict] = []
        self.nonce_counter = 0
        self.packet_record: list[dict] = []

    def _log(self, event: str, details: dict = None) -> None:
        entry = {"time_ms": time.time() * 1000, "event": event,
                 "state": self.state.name, "details": details or {}}
        self.log.append(entry)

    def _make_nonce(self) -> bytes:
        self.nonce_counter += 1
        return struct.pack('>H I I', self.device_addr, self.session_id, self.nonce_counter) + b'\x00' * 2

    def _make_packet(self, ptype: int, payload: bytes, encrypt: bool = False) -> Packet:
        pkt = Packet(ptype=ptype, seq=self.tx_seq, payload=payload, device_addr=self.device_addr)
        if encrypt and self.session_key:
            nonce = self._make_nonce()
            aad = struct.pack('>BBH B', 0xAA, ptype, self.tx_seq, self.device_addr)
            ct, tag = CryptoEngine.encrypt(self.session_key, nonce, payload, aad)
            pkt.payload = ct
            pkt.auth_tag = tag
            pkt._nonce = nonce  # type: ignore
        self.tx_seq = (self.tx_seq + 1) & 0xFFFF
        return pkt

    def _check_seq(self, seq: int) -> bool:
        if seq > self.rx_window_max:
            self.rx_window_max = seq
            self.rx_seq = seq
            return True
        if seq >= self.rx_window_max - self.auth_window and seq <= self.rx_window_max:
            return True
        return False

    def process_packet(self, raw: bytes) -> Optional[Packet]:
        pkt = Packet.decode(raw)
        if pkt is None:
            self._log("INVALID_PACKET", {"size": len(raw)})
            return None

        record = {"dir": "rx", "ptype": pkt.ptype, "seq": pkt.seq,
                   "size": len(raw), "encrypted": len(pkt.auth_tag) == 8}
        self.packet_record.append(record)

        if self.state == ProtoState.SLEEP:
            if pkt.ptype == 0:  # session request
                self.state = ProtoState.AUTH
                self.session_id += 1
                import secrets
                self.challenge = secrets.token_bytes(16)
                self._log("SESSION_REQ", {"session_id": self.session_id})
                resp = self._make_packet(1, self.challenge)  # challenge
                resp._nonce = b''  # type: ignore  # unencrypted challenge
                return resp

        elif self.state == ProtoState.AUTH:
            if pkt.ptype == 2 and self.challenge:  # response (auth proof)
                # Verify HMAC of challenge
                expected = hmac.new(self.psk, self.challenge, hashlib.sha256).digest()[:16]
                if hmac.compare_digest(pkt.payload, expected):
                    # Derive session key
                    self.session_key = CryptoEngine.derive_key(
                        self.psk, self.challenge, f"session-{self.session_id}")
                    self.session_nonce = self.challenge[:12]
                    self.tx_seq = 0
                    self.rx_seq = 0
                    self.rx_window_max = 0
                    self.state = ProtoState.ACTIVE
                    self._log("AUTH_SUCCESS", {"session_id": self.session_id})
                    return self._make_packet(3, b'SESSION_OK')
                else:
                    self._log("AUTH_FAIL", {"session_id": self.session_id})
                    self.state = ProtoState.IDLE
                    return Packet(ptype=5, seq=0, payload=b'AUTH_FAIL')

        elif self.state == ProtoState.ACTIVE:
            if not self._check_seq(pkt.seq):
                self._log("REPLAY_DETECTED", {"pkt_seq": pkt.seq, "expected": self.rx_seq})
                return Packet(ptype=5, seq=0, payload=b'REPLAY')
            self.rx_seq = pkt.seq

            if pkt.ptype == 4:  # data (command)
                if self.session_key and len(pkt.auth_tag) == 8:
                    nonce = self._make_nonce()
                    aad = struct.pack('>BBH B', 0xAA, pkt.ptype, pkt.seq, pkt.device_addr)
                    pt = CryptoEngine.decrypt(self.session_key, nonce, pkt.payload, aad, pkt.auth_tag)
                    if pt is None:
                        self._log("AUTH_FAIL_DATA", {"seq": pkt.seq})
                        return Packet(ptype=5, seq=0, payload=b'AUTH_FAIL')
                    self._log("COMMAND_RECEIVED", {"seq": pkt.seq, "decrypted_size": len(pt)})
                    return self._make_packet(4, b'ACK_CMD:' + pt, encrypt=True)
                else:
                    self._log("COMMAND_UNENCRYPTED", {"seq": pkt.seq})
                    return Packet(ptype=5, seq=0, payload=b'UNENCRYPTED_REJECTED')

            elif pkt.ptype == 6:  # session end
                self.state = ProtoState.IDLE
                self.session_key = None
                self._log("SESSION_END", {})
                return Packet(ptype=5, seq=0, payload=b'BYE')

        self._log("UNHANDLED", {"state": self.state.name, "ptype": pkt.ptype})
        return None


class ProgrammerProtocol:
    """Simulated programmer-side protocol."""
    def __init__(self, implant: ImplantProtocol) -> None:
        self.implant = implant
        self.psk = implant.psk
        self.tx_seq = 0
        self.session_key: Optional[bytes] = None

    def initiate_session(self) -> Optional[Packet]:
        self.implant.state = ProtoState.IDLE  # wake
        req = Packet(ptype=0, seq=0, device_addr=self.implant.device_addr)
        resp = self.implant.process_packet(req.encode())
        return resp

    def authenticate(self, challenge: bytes) -> Optional[Packet]:
        proof = hmac.new(self.psk, challenge, hashlib.sha256).digest()[:16]
        req = Packet(ptype=2, seq=0, payload=proof)
        return self.implant.process_packet(req.encode())

    def send_command(self, cmd: bytes) -> Optional[Packet]:
        if not self.session_key:
            # Derive same key
            self.session_key = CryptoEngine.derive_key(
                self.psk, self.implant.challenge or b'',
                f"session-{self.implant.session_id}")
        nonce = struct.pack('>H I I', self.implant.device_addr, self.implant.session_id, 1) + b'\x00' * 2
        aad = struct.pack('>BBH B', 0xAA, 4, self.tx_seq, self.implant.device_addr)
        ct, tag = CryptoEngine.encrypt(self.session_key, nonce, cmd, aad)
        pkt = Packet(ptype=4, seq=self.tx_seq, payload=ct, auth_tag=tag,
                      device_addr=self.implant.device_addr)
        self.tx_seq += 1
        return self.implant.process_packet(pkt.encode())

    def end_session(self) -> Optional[Packet]:
        return self.implant.process_packet(Packet(ptype=6, seq=self.tx_seq).encode())


def demo_mode() -> None:
    print("=" * 60)
    print("VIREON Protocol Simulator: Session Demo")
    print("=" * 60)

    implant = ImplantProtocol()
    programmer = ProgrammerProtocol(implant)

    print("\n[1] Initiating session...")
    resp = programmer.initiate_session()
    if resp:
        print(f"  Challenge received: {resp.payload.hex()[:32]}...")

    print("\n[2] Authenticating...")
    resp = programmer.authenticate(implant.challenge or b'')
    if resp:
        print(f"  Auth result: {resp.payload}")
        print(f"  Implant state: {implant.state.name}")

    print("\n[3] Sending encrypted commands...")
    cmds = [b'SET_AMPLITUDE:3.0', b'SET_FREQ:130', b'GET_STATUS']
    for cmd in cmds:
        resp = programmer.send_command(cmd)
        if resp:
            print(f"  CMD: {cmd.decode()} -> {resp.payload[:40]}")

    print("\n[4] Ending session...")
    resp = programmer.end_session()
    if resp:
        print(f"  Session ended: {resp.payload}")

    print(f"\n  Total packets logged: {len(implant.packet_record)}")
    print(f"  Security events: {len(implant.log)}")

    # Export
    out = {"log": implant.log, "packets": implant.packet_record,
           "session_id": implant.session_id}
    os.makedirs("./output", exist_ok=True)
    with open("./output/protocol_session.json", 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n  Session exported: ./output/protocol_session.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="VIREON Protocol Simulator")
    parser.add_argument("--mode", choices=["demo"], default="demo")
    args = parser.parse_args()
    demo_mode()


if __name__ == "__main__":
    main()
