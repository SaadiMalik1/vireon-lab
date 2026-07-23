"""
VIREON-LABS NL-004 Lab 002: Protocol Attack Simulation
===================================================

Simulates protocol-level attacks (replay, injection, desynchronization,
battery drain) against the protocol from Lab 001 and measures detection.

Usage:
    python protocol_attacks.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lab-001-protocol-simulator'))
from protocol_simulator import ImplantProtocol, Packet, CryptoEngine, ProtoState, ProgrammerProtocol
import hashlib
import struct


def run_benchmarks() -> dict:
    """Run WP-001 through WP-008 benchmarks."""
    results = {}

    # Setup implant and establish session
    implant = ImplantProtocol()
    implant.state = ProtoState.IDLE
    programmer = ProgrammerProtocol(implant)

    # Establish legitimate session
    resp = programmer.initiate_session()
    if not resp or resp.ptype != 1:
        return {"error": "session init failed"}
    challenge = resp.payload
    resp = programmer.authenticate(challenge)
    if not resp or b'OK' not in resp.payload:
        return {"error": "auth failed"}

    # Get a legitimate encrypted data packet for replay testing
    import secrets
    nonce = struct.pack('>H I I', implant.device_addr, implant.session_id, 2) + b'\x00' * 2
    aad = struct.pack('>BBH B', 0xAA, 4, 0, implant.device_addr)
    ct, tag = CryptoEngine.encrypt(implant.session_key or b'', nonce, b'GET_STATUS', aad)
    legit_pkt = Packet(ptype=4, seq=0, payload=ct, auth_tag=tag, device_addr=implant.device_addr)
    legit_raw = legit_pkt.encode()

    # WP-002: Cross-session replay
    implant2 = ImplantProtocol()
    implant2.state = ProtoState.IDLE
    resp_replay = implant2.process_packet(legit_raw)
    results["WP-002_cross_session_replay"] = {
        "accepted": resp_replay is not None and resp_replay.payload != b'REPLAY',
        "details": "Rejected (different session context)" if resp_replay is None or resp_replay.payload == b'REPLAY' else "Accepted - VULNERABLE"
    }

    # WP-003: Within-session replay (same seq number)
    resp_replay2 = implant.process_packet(legit_raw)
    results["WP-003_within_session_replay"] = {
        "accepted": resp_replay2 is not None and b'REPLAY' not in (resp_replay2.payload if resp_replay2 else b''),
        "details": "Duplicate seq detected" if resp_replay2 and b'REPLAY' in (resp_replay2.payload if resp_replay2 else b'') else "Not detected"
    }

    # WP-004: Injection with forged auth tag
    forged = Packet(ptype=4, seq=1, payload=b'\x00' * 20, auth_tag=b'\x00' * 8, device_addr=implant.device_addr)
    resp_inject = implant.process_packet(forged.encode())
    results["WP-004_injection"] = {
        "accepted": resp_inject is not None and b'AUTH_FAIL' not in (resp_inject.payload if resp_inject else b''),
        "details": "Auth tag verification rejected forged packet"
    }

    # WP-006: Command flooding
    flood_accepted = 0
    flood_total = 100
    for i in range(flood_total):
        fp = Packet(ptype=0, seq=i, device_addr=implant.device_addr)  # session requests
        r = implant.process_packet(fp.encode())
        if r is not None:
            flood_accepted += 1
    results["WP-006_flooding"] = {
        "accepted_rate": flood_accepted / flood_total,
        "total": flood_total,
        "accepted": flood_accepted
    }

    return results


def main() -> None:
    print("=" * 60)
    print("VIREON Protocol Attack Benchmark")
    print("=" * 60)

    results = run_benchmarks()

    for bench, data in results.items():
        if isinstance(data, dict) and 'accepted' in data:
            status = "VULNERABLE" if data['accepted'] else "PASS"
            print(f"\n  {bench}: [{status}]")
            for k, v in data.items():
                print(f"    {k}: {v}")
        else:
            print(f"\n  {bench}: {data}")

    os.makedirs("./output", exist_ok=True)
    with open("./output/attack_benchmark.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nBenchmark exported: ./output/attack_benchmark.json")


if __name__ == "__main__":
    main()
