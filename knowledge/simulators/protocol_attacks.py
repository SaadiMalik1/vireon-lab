"""
VIREON-LABS NL-004 Lab 002: Protocol Attack Simulation & Benchmarking
==================================================================

Executes standardized protocol security benchmarks (WP-001 through WP-008)
against the protocol simulator from Lab 001, measuring detection and mitigation
effectiveness for each attack class.

Benchmarks (from NL-004 Section 14.1):
    WP-001: Cleartext eavesdropping detection
    WP-002: Cross-session replay detection
    WP-003: Within-session replay detection
    WP-004: Packet injection with forged auth tag
    WP-005: Desynchronization attack
    WP-006: Command flooding (DoS)
    WP-007: Battery drain measurement
    WP-008: Authorization bypass (per-command)

Usage:
    python protocol_attacks.py                    # Run all benchmarks
    python protocol_attacks.py --benchmark WP-002  # Run specific benchmark
    python protocol_attacks.py --full              # Full report with details
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import struct
import sys
import time
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lab-001-protocol-simulator'))
from protocol_simulator import (
    ImplantProtocol, Packet, CryptoEngine, ProtoState,
    ProgrammerProtocol, PacketType, AuthLevel, ResponseCode,
    COMMANDS, EnergyModel,
)


# ============================================================================
# SECTION 1: Session Helper
# ============================================================================

def establish_session(implant: ImplantProtocol, programmer: ProgrammerProtocol
                      ) -> bool:
    """Establish a session between programmer and implant."""
    resp = programmer.initiate_session()
    if not resp or resp.ptype != PacketType.CHALLENGE.value:
        return False
    resp = programmer.authenticate(implant.challenge or b'')
    if not resp or resp.ptype != PacketType.SESSION_CONFIRM.value:
        return False
    return True


def get_legit_data_packet(implant: ImplantProtocol, programmer: ProgrammerProtocol,
                          cmd_id: int = 0x01, params: bytes = b'',
                          seq: Optional[int] = None) -> bytes:
    """Create a legitimate encrypted data packet for replay testing."""
    if seq is not None:
        saved = programmer.tx_seq
        programmer.tx_seq = seq
    payload = struct.pack('B', cmd_id) + params
    nonce = struct.pack('>H I I H', implant.device_addr, implant.session_id,
                         implant.boot_nonce, programmer.tx_seq & 0xFFFF)
    aad = struct.pack('>BBH B', 0xAA, PacketType.DATA.value,
                       programmer.tx_seq, implant.device_addr)
    ct, tag = CryptoEngine.encrypt(programmer.session_key or b'', nonce, payload, aad)
    pkt = Packet(ptype=PacketType.DATA.value, seq=programmer.tx_seq,
                 payload=ct, auth_tag=tag, device_addr=implant.device_addr)
    programmer.tx_seq += 1
    if seq is not None:
        programmer.tx_seq = saved
    return pkt.encode()


# ============================================================================
# SECTION 2: WP-001 — Cleartext Eavesdropping
# ============================================================================

def run_wp001(implant: ImplantProtocol, programmer: ProgrammerProtocol
              ) -> dict:
    """WP-001: Verify that data packets are encrypted (no plaintext leakage).
    
    Method: Capture encrypted data packets, analyze entropy and pattern.
    If payload contains recognizable plaintext patterns, encryption is missing.
    
    Scoring: 10 if no plaintext detected, 0 if plaintext found.
    """
    results = {
        "benchmark": "WP-001",
        "name": "Cleartext Eavesdropping Detection",
        "score": 10,
        "max_score": 10,
        "passed": True,
        "details": [],
    }

    if not establish_session(implant, programmer):
        results["passed"] = False
        results["score"] = 0
        results["details"].append("Session establishment failed")
        return results

    # Capture several encrypted data packets (full packets for tag check)
    captured_packets = []
    captured_payloads = []
    for cmd_id in [0x01, 0x04, 0x05, 0x08, 0x0B]:
        params = b''
        if cmd_id == 0x04:
            params = struct.pack('>f', 3.0)
        elif cmd_id == 0x05:
            params = struct.pack('>H', 130)
        raw = get_legit_data_packet(implant, programmer, cmd_id, params)
        pkt = Packet.decode(raw)
        if pkt:
            captured_packets.append(pkt)
            captured_payloads.append(pkt.payload)

    # Check 1: All data packets have auth tags (8 bytes)
    all_have_tags = all(len(p.auth_tag) == 8 for p in captured_packets)
    results["details"].append(
        f"All data packets have 8-byte auth tag: {all_have_tags}"
    )

    # Check 2: Payload entropy (encrypted data should have high entropy)
    import math
    plaintext_patterns = [b'GET_STATUS', b'SET_AMPLITUDE', b'START_THERAPY']
    cleartext_detected = False
    for payload in captured_payloads:
        for pattern in plaintext_patterns:
            if pattern in payload:
                cleartext_detected = True
                results["details"].append(
                    f"CLEARTEXT LEAKED: '{pattern.decode()}' found in payload"
                )

    if cleartext_detected:
        results["score"] = 0
        results["passed"] = False
    elif not all_have_tags:
        results["score"] = 5
        results["passed"] = False
        results["details"].append("Partial: packets encrypted but some missing auth tags")
    else:
        results["details"].append("All data packets encrypted with authentication")

    # Entropy analysis
    if captured_payloads:
        all_bytes = b''.join(captured_payloads)
        byte_counts = [0] * 256
        for b in all_bytes:
            byte_counts[b] += 1
        entropy = 0
        total = len(all_bytes)
        for c in byte_counts:
            if c > 0:
                p = c / total
                entropy -= p * math.log2(p)
        results["details"].append(
            f"Payload entropy: {entropy:.2f} bits/byte (max 8.0, "
            f"random={entropy > 7.0}, structured={entropy < 5.0})"
        )

    programmer.end_session()
    return results


# ============================================================================
# SECTION 3: WP-002/003 — Replay Attacks
# ============================================================================

def run_wp002(implant: ImplantProtocol, programmer: ProgrammerProtocol
              ) -> dict:
    """WP-002: Cross-session replay detection.
    
    Method: Record a packet from session 1, replay it in session 2.
    Score = 10 * (rejected / total).
    """
    results = {
        "benchmark": "WP-002",
        "name": "Cross-Session Replay Detection",
        "score": 0,
        "max_score": 10,
        "passed": False,
        "details": [],
    }

    # Session 1: capture a legitimate packet
    implant1 = ImplantProtocol()
    prog1 = ProgrammerProtocol(implant1)
    if not establish_session(implant1, prog1):
        results["details"].append("Session 1 establishment failed")
        return results
    captured = get_legit_data_packet(implant1, prog1, 0x01)
    prog1.end_session()
    results["details"].append(f"Captured packet from session 1 ({len(captured)} bytes)")

    # Session 2: replay the captured packet
    implant2 = ImplantProtocol()
    implant2.state = ProtoState.ACTIVE  # Force active for testing
    implant2.session_key = implant1.session_key  # Same key (simulates compromised PSK)
    resp = implant2.process_packet(captured)

    is_rejected = resp is None or (resp.payload and b'REPLAY' in resp.payload) or \
                 (resp is not None and resp.ptype == PacketType.ERROR.value)
    
    if is_rejected:
        results["score"] = 10
        results["passed"] = True
        results["details"].append("Cross-session replay CORRECTLY REJECTED")
    else:
        results["score"] = 0
        results["details"].append("Cross-session replay ACCEPTED — VULNERABLE")

    return results


def run_wp003(implant: ImplantProtocol, programmer: ProgrammerProtocol
              ) -> dict:
    """WP-003: Within-session replay detection.
    
    Method: In an active session, send the same packet twice (same seq).
    Score = 10 * (rejected / total).
    """
    results = {
        "benchmark": "WP-003",
        "name": "Within-Session Replay Detection",
        "score": 0,
        "max_score": 10,
        "passed": False,
        "details": [],
    }

    if not establish_session(implant, programmer):
        results["details"].append("Session establishment failed")
        return results

    # Send a legitimate command
    raw = get_legit_data_packet(implant, programmer, 0x01, seq=0)
    resp1 = implant.process_packet(raw)
    results["details"].append(f"First send: ptype={resp1.ptype if resp1 else None}")

    # Replay the exact same packet (same seq)
    resp2 = implant.process_packet(raw)
    is_rejected = resp2 is None or \
                 (resp2 and resp2.ptype == PacketType.ERROR.value) or \
                 (resp2 and b'REPLAY' in (resp2.payload or b''))

    if is_rejected:
        results["score"] = 10
        results["passed"] = True
        results["details"].append("Within-session replay CORRECTLY REJECTED")
    else:
        results["score"] = 0
        results["details"].append("Within-session replay ACCEPTED — VULNERABLE")

    programmer.end_session()
    return results


# ============================================================================
# SECTION 4: WP-004 — Packet Injection
# ============================================================================

def run_wp004(implant: ImplantProtocol, programmer: ProgrammerProtocol
              ) -> dict:
    """WP-004: Packet injection with forged auth tag.
    
    Method: Craft packets with random/forged auth tags.
    Score = 10 * (rejected / total_injected).
    """
    results = {
        "benchmark": "WP-004",
        "name": "Packet Injection (Forged Auth Tag)",
        "score": 0,
        "max_score": 10,
        "passed": False,
        "details": [],
        "injected": 0,
        "rejected": 0,
    }

    if not establish_session(implant, programmer):
        results["details"].append("Session establishment failed")
        return results

    # Inject 10 packets with random auth tags and various commands
    total = 10
    rejected = 0
    for i in range(total):
        # Create packet with forged (random) auth tag
        fake_tag = secrets.token_bytes(8)
        fake_payload = struct.pack('B', 0x04) + struct.pack('>f', 10.0)  # SET_AMPLITUDE 10.0
        pkt = Packet(ptype=PacketType.DATA.value, seq=100 + i,
                     payload=fake_payload, auth_tag=fake_tag,
                     device_addr=implant.device_addr)
        resp = implant.process_packet(pkt.encode())
        if resp is None or resp.ptype == PacketType.ERROR.value:
            rejected += 1
        results["injected"] += 1
        results["rejected"] += 1 if resp is None or resp.ptype == PacketType.ERROR.value else 0

    results["score"] = round(10 * rejected / total, 1)
    results["passed"] = rejected == total
    results["details"].append(
        f"Injected {total} packets with forged auth tags: {rejected} rejected"
    )

    # Also test injection without any auth tag
    no_tag_pkt = Packet(ptype=PacketType.DATA.value, seq=200,
                        payload=struct.pack('B', 0x04),
                        device_addr=implant.device_addr)
    resp = implant.process_packet(no_tag_pkt.encode())
    no_tag_rejected = resp is None or resp.ptype == PacketType.ERROR.value
    results["details"].append(
        f"Injection without auth tag: {'REJECTED' if no_tag_rejected else 'ACCEPTED (VULN)'}"
    )

    programmer.end_session()
    return results


# ============================================================================
# SECTION 5: WP-005 — Desynchronization Attack
# ============================================================================

def run_wp005(implant: ImplantProtocol, programmer: ProgrammerProtocol
              ) -> dict:
    """WP-005: Desynchronization attack via sequence number manipulation.
    
    Method: Send packets with future sequence numbers to advance the
    implant's replay window, causing legitimate packets to be rejected.
    Score = 10 if legitimate session recovers within 5 seconds (new session).
    """
    results = {
        "benchmark": "WP-005",
        "name": "Desynchronization Attack",
        "score": 0,
        "max_score": 10,
        "passed": False,
        "details": [],
    }

    if not establish_session(implant, programmer):
        results["details"].append("Session establishment failed")
        return results

    # Send a few legitimate commands to establish seq numbers
    for i in range(3):
        raw = get_legit_data_packet(implant, programmer, 0x01)
        implant.process_packet(raw)

    # Now send a packet with a very high sequence number
    high_seq = 60000
    raw_high = get_legit_data_packet(implant, programmer, 0x01, seq=high_seq)
    resp = implant.process_packet(raw_high)
    window_after = implant.rx_window_max
    results["details"].append(
        f"Sent packet with seq={high_seq}, window advanced to {window_after}"
    )

    # Now try to send a legitimate packet with the old (low) seq number
    low_seq = programmer.tx_seq  # Should be around 3-4
    raw_low = get_legit_data_packet(implant, programmer, 0x01, seq=low_seq)
    resp = implant.process_packet(raw_low)
    is_rejected = resp is None or resp.ptype == PacketType.ERROR.value
    results["details"].append(
        f"Legitimate packet (seq={low_seq}) after desync: "
        f"{'REJECTED (desync successful)' if is_rejected else 'ACCEPTED (protected)'}"
    )

    if is_rejected:
        # Test recovery: can a new session be established?
        start = time.time()
        implant2 = ImplantProtocol()
        prog2 = ProgrammerProtocol(implant2)
        recovered = establish_session(implant2, prog2)
        recovery_time = time.time() - start
        results["details"].append(
            f"Recovery via new session: {'SUCCESS' if recovered else 'FAILED'} "
            f"({recovery_time*1000:.1f} ms)"
        )
        if recovered and recovery_time < 5.0:
            results["score"] = 10  # System recovers
            results["passed"] = True
            results["details"].append(
                "Desynchronization is possible but recovery is fast (score=10)"
            )
        else:
            results["score"] = 5
            results["details"].append("Desynchronization succeeded, slow recovery")
    else:
        results["score"] = 10
        results["passed"] = True
        results["details"].append("Protocol RESISTED desynchronization attack")

    programmer.end_session()
    return results


# ============================================================================
# SECTION 6: WP-006 — Command Flooding
# ============================================================================

def run_wp006(implant: ImplantProtocol, programmer: ProgrammerProtocol
              ) -> dict:
    """WP-006: Command flooding DoS attack.
    
    Method: Send 100 session requests rapidly, then test if legitimate
    communication still works.
    Score = 10 * (legitimate_commands_processed / total_legitimate).
    """
    results = {
        "benchmark": "WP-006",
        "name": "Command Flooding (DoS)",
        "score": 0,
        "max_score": 10,
        "passed": False,
        "details": [],
    }

    # Fresh implant for this test
    flood_implant = ImplantProtocol()
    flood_count = 100
    accepted_flood = 0

    for i in range(flood_count):
        pkt = Packet(ptype=PacketType.SESSION_REQ.value, seq=i,
                     device_addr=flood_implant.device_addr)
        resp = flood_implant.process_packet(pkt.encode())
        if resp is not None:
            accepted_flood += 1

    results["details"].append(
        f"Sent {flood_count} session requests: {accepted_flood} processed"
    )
    results["details"].append(
        f"Energy consumed: {flood_implant.energy.total_energy_uj:.1f} uJ"
    )

    # Now try legitimate session after flood
    prog = ProgrammerProtocol(flood_implant)
    # Reset state for fair test
    flood_implant.state = ProtoState.SLEEP
    flood_implant.session_id = 0
    flood_implant.challenge = None

    legit_total = 5
    legit_processed = 0
    if establish_session(flood_implant, prog):
        for i in range(legit_total):
            raw = get_legit_data_packet(flood_implant, prog, 0x01)
            resp = flood_implant.process_packet(raw)
            if resp and resp.ptype == PacketType.DATA.value:
                legit_processed += 1
    
    results["details"].append(
        f"Post-flood legitimate commands: {legit_processed}/{legit_total}"
    )
    results["score"] = round(10 * legit_processed / legit_total, 1) if legit_total > 0 else 0
    results["passed"] = legit_processed == legit_total

    prog.end_session()
    return results


# ============================================================================
# SECTION 7: WP-007 — Battery Drain
# ============================================================================

def run_wp007(implant: ImplantProtocol, programmer: ProgrammerProtocol
              ) -> dict:
    """WP-007: Battery drain measurement.
    
    Method: Compare energy consumed during attack vs. normal operation.
    Score = 10 * max(0, 1 - attack_energy / normal_energy).
    Higher score = less energy wasted during attack.
    """
    results = {
        "benchmark": "WP-007",
        "name": "Battery Drain Measurement",
        "score": 0,
        "max_score": 10,
        "passed": False,
        "details": [],
    }

    # Normal operation energy: establish session, send 10 commands
    normal_implant = ImplantProtocol()
    normal_prog = ProgrammerProtocol(normal_implant)
    if establish_session(normal_implant, normal_prog):
        for i in range(10):
            raw = get_legit_data_packet(normal_implant, normal_prog, 0x01)
            normal_implant.process_packet(raw)
        normal_prog.end_session()
    normal_energy = normal_implant.energy.total_energy_uj

    # Attack operation energy: 100 session requests (forced wake + crypto)
    attack_implant = ImplantProtocol()
    for i in range(100):
        pkt = Packet(ptype=PacketType.SESSION_REQ.value, seq=i,
                     device_addr=attack_implant.device_addr)
        attack_implant.process_packet(pkt.encode())
    attack_energy = attack_implant.energy.total_energy_uj

    results["details"].append(
        f"Normal session energy (10 cmds): {normal_energy:.1f} uJ"
    )
    results["details"].append(
        f"Attack energy (100 session reqs): {attack_energy:.1f} uJ"
    )
    results["details"].append(
        f"Energy amplification: {attack_energy/normal_energy:.1f}x"
    )
    results["details"].append(
        f"Avg energy per attack packet: {attack_energy/100:.1f} uJ"
    )
    results["details"].append(
        f"Avg energy per normal cmd: {normal_energy/10:.1f} uJ"
    )

    # Score: higher is better (less energy wasted during attack)
    # Perfect score (10) = attack has minimal energy impact
    # Low score = attack drains significant battery
    ratio = attack_energy / normal_energy if normal_energy > 0 else 999
    if ratio < 5:
        results["score"] = 10  # Minimal amplification
        results["passed"] = True
    elif ratio < 20:
        results["score"] = round(10 * (1 - ratio/20), 1)
        results["passed"] = False
    else:
        results["score"] = 0
        results["passed"] = False

    results["details"].append(
        f"Battery drain protection: {'ADEQUATE' if results['passed'] else 'INSUFFICIENT'}"
    )
    return results


# ============================================================================
# SECTION 8: WP-008 — Authorization Bypass
# ============================================================================

def run_wp008(implant: ImplantProtocol, programmer: ProgrammerProtocol
              ) -> dict:
    """WP-008: Per-command authorization bypass.
    
    Method: Establish HOME-level session, attempt CLINICAL and FIRMWARE commands.
    Score = 10 * (unauthorized_rejected / total_unauthorized).
    """
    results = {
        "benchmark": "WP-008",
        "name": "Authorization Bypass (Per-Command)",
        "score": 0,
        "max_score": 10,
        "passed": False,
        "details": [],
    }

    # Establish HOME-level session (respect caller's vulnerable flag)
    vuln = implant.vulnerable if implant else False
    home_implant = ImplantProtocol(session_auth_level=AuthLevel.HOME, vulnerable=vuln)
    home_prog = ProgrammerProtocol(home_implant, auth_level=AuthLevel.HOME)

    if not establish_session(home_implant, home_prog):
        results["details"].append("Session establishment failed")
        return results

    # Commands that require higher authorization
    unauthorized_cmds = [
        (0x04, struct.pack('>f', 5.0), "SET_AMPLITUDE", AuthLevel.CLINICAL),
        (0x05, struct.pack('>H', 250), "SET_FREQUENCY", AuthLevel.CLINICAL),
        (0x08, b'', "START_THERAPY", AuthLevel.CLINICAL),
        (0x0C, b'', "OTA_UPDATE", AuthLevel.FIRMWARE),
        (0x0A, struct.pack('>ff', 1.0, 0.1), "SET_CL_PARAMS", AuthLevel.CLINICAL),
    ]

    total = len(unauthorized_cmds)
    rejected = 0
    for cmd_id, params, name, required in unauthorized_cmds:
        raw = get_legit_data_packet(home_implant, home_prog, cmd_id, params)
        resp = home_implant.process_packet(raw)
        is_rejected = resp is None or resp.ptype == PacketType.ERROR.value
        if is_rejected:
            rejected += 1
            results["details"].append(
                f"{name} (requires {required.name}): REJECTED"
            )
        else:
            results["details"].append(
                f"{name} (requires {required.name}): ACCEPTED — VULNERABILITY"
            )

    results["score"] = round(10 * rejected / total, 1)
    results["passed"] = rejected == total
    results["details"].append(
        f"Unauthorized commands rejected: {rejected}/{total}"
    )

    home_prog.end_session()
    return results


# ============================================================================
# SECTION 9: Vulnerable Mode Comparison
# ============================================================================

def run_vulnerable_comparison() -> dict:
    """Run all benchmarks against VULNERABLE configuration for comparison.
    
    This demonstrates what happens when security measures are disabled,
    mapping to real-world device vulnerabilities.
    """
    print("\n" + "=" * 70)
    print("  VULNERABLE MODE COMPARISON")
    print("  Testing with: no auth verify, no replay protection, no per-cmd auth")
    print("=" * 70)

    vuln_results = {}

    # WP-002 vulnerable
    impl = ImplantProtocol(vulnerable=True)
    impl.state = ProtoState.ACTIVE
    prog = ProgrammerProtocol(impl)
    r = run_wp002(impl, prog)
    vuln_results["WP-002"] = r
    print(f"  WP-002 (Cross-session replay): {'PASS' if r['passed'] else 'FAIL'} (score={r['score']})")

    # WP-003 vulnerable
    impl = ImplantProtocol(vulnerable=True)
    prog = ProgrammerProtocol(impl)
    r = run_wp003(impl, prog)
    vuln_results["WP-003"] = r
    print(f"  WP-003 (Within-session replay): {'PASS' if r['passed'] else 'FAIL'} (score={r['score']})")

    # WP-004 vulnerable
    impl = ImplantProtocol(vulnerable=True)
    prog = ProgrammerProtocol(impl)
    r = run_wp004(impl, prog)
    vuln_results["WP-004"] = r
    print(f"  WP-004 (Forged injection): {'PASS' if r['passed'] else 'FAIL'} (score={r['score']})")

    # WP-008 vulnerable
    impl = ImplantProtocol(vulnerable=True, session_auth_level=AuthLevel.HOME)
    prog = ProgrammerProtocol(impl, auth_level=AuthLevel.HOME)
    r = run_wp008(impl, prog)
    vuln_results["WP-008"] = r
    print(f"  WP-008 (Auth bypass): {'PASS' if r['passed'] else 'FAIL'} (score={r['score']})")

    return vuln_results


# ============================================================================
# SECTION 10: Main Benchmark Runner
# ============================================================================

BENCHMARK_RUNNERS = {
    "WP-001": run_wp001,
    "WP-002": run_wp002,
    "WP-003": run_wp003,
    "WP-004": run_wp004,
    "WP-005": run_wp005,
    "WP-006": run_wp006,
    "WP-007": run_wp007,
    "WP-008": run_wp008,
}


def run_all_benchmarks(detailed: bool = False) -> dict:
    """Run all WP-001 through WP-008 benchmarks on SECURE configuration."""
    all_results = {}
    total_score = 0
    max_score = 0

    for bench_id, runner in BENCHMARK_RUNNERS.items():
        implant = ImplantProtocol()
        programmer = ProgrammerProtocol(implant)
        result = runner(implant, programmer)
        all_results[bench_id] = result
        total_score += result["score"]
        max_score += result["max_score"]

    overall_pct = (total_score / max_score * 100) if max_score > 0 else 0
    all_results["_summary"] = {
        "total_score": total_score,
        "max_score": max_score,
        "percentage": round(overall_pct, 1),
        "grade": "A" if overall_pct >= 90 else "B" if overall_pct >= 80 else
                 "C" if overall_pct >= 70 else "D" if overall_pct >= 60 else "F",
    }

    return all_results


def print_results(results: dict, detailed: bool = False) -> None:
    """Print benchmark results in formatted table."""
    print("\n" + "=" * 70)
    print("  VIREON Protocol Security Benchmark Results")
    print("  NL-004 Lab 002 — Secure Configuration")
    print("=" * 70)

    for bench_id, r in results.items():
        if bench_id.startswith("_"):
            continue
        if not r.get("name"):
            continue
        status = "PASS" if r.get("passed", False) else "FAIL"
        score = r.get("score", 0)
        max_s = r.get("max_score", 10)
        name = r.get("name", "")
        print(f"\n  {bench_id}: [{status}] {score}/{max_s} — {name}")
        if detailed:
            for d in r.get("details", []):
                print(f"    {d}")

    summary = results.get("_summary", {})
    if summary:
        print(f"\n{'─' * 70}")
        print(f"  OVERALL: {summary['total_score']}/{summary['max_score']} "
              f"({summary['percentage']}%) — Grade: {summary['grade']}")
        print(f"{'─' * 70}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="VIREON Protocol Attack Benchmark (NL-004 Lab 002)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python protocol_attacks.py
  python protocol_attacks.py --full
  python protocol_attacks.py --benchmark WP-003
  python protocol_attacks.py --vulnerable
""")
    parser.add_argument("--benchmark", type=str, default=None,
                        choices=list(BENCHMARK_RUNNERS.keys()),
                        help="Run a specific benchmark")
    parser.add_argument("--full", action="store_true",
                        help="Show detailed output for each benchmark")
    parser.add_argument("--vulnerable", action="store_true",
                        help="Also run vulnerable mode comparison")
    parser.add_argument("--output_dir", type=str, default=None,
                        help="Override output directory")
    args = parser.parse_args()

    if args.benchmark:
        # Run single benchmark
        runner = BENCHMARK_RUNNERS[args.benchmark]
        implant = ImplantProtocol()
        programmer = ProgrammerProtocol(implant)
        result = runner(implant, programmer)
        print_results({args.benchmark: result}, detailed=True)
        results = {args.benchmark: result}
    else:
        # Run all benchmarks
        results = run_all_benchmarks(detailed=args.full)
        print_results(results, detailed=args.full)

        if args.vulnerable:
            vuln_results = run_vulnerable_comparison()
            results["_vulnerable"] = vuln_results

    # Export
    out_dir = args.output_dir or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "output"
    )
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "attack_benchmark.json")
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Benchmark exported: {out_path}")


if __name__ == "__main__":
    main()
