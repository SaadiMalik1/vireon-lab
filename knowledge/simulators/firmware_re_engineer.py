"""
VIREON-LABS NL-003 Lab 002: Firmware Reverse Engineering
======================================================

Static and dynamic analysis of the simulated firmware binary
produced by Lab 001. Demonstrates: string extraction, pattern
detection, vector table parsing, function region identification,
and security annotation.

Learning Objectives:
    1. Extract security-relevant strings from a firmware binary
    2. Identify the vector table and interrupt handler addresses
    3. Locate known code patterns (AES S-box, filter coefficients)
    4. Map the firmware's functional regions (safety, DSP, comms)
    5. Produce a VIREON FirmwareAnalysisReport

Required Software: Python 3.9+
Required Hardware: None
Estimated Time: 5-6 hours
Difficulty: Intermediate-Advanced

Usage:
    python firmware_re_engineer.py --binary ../lab-001/output/simulated_firmware.bin
    python firmware_re_engineer.py --binary ../lab-001/output/simulated_firmware.bin --full
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
from dataclasses import dataclass, field, asdict
from typing import Optional


# ============================================================================
# Analysis Data Structures
# ============================================================================

@dataclass
class FirmwareRegion:
    """A contiguous region of the firmware binary."""
    name: str
    start_offset: int
    end_offset: int
    size_bytes: int
    region_type: str  # code, data, string, unknown, crypto, safety, comms
    security_relevance: str  # critical, high, medium, low
    annotations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VectorTableEntry:
    """One entry in the ARM Cortex-M vector table."""
    index: int
    name: str
    address: int
    security_note: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StringMatch:
    """A string extracted from the firmware binary."""
    offset: int
    string: str
    security_relevance: str  # critical, high, medium, low, info
    category: str  # version, error, debug, crypto, safety, unknown

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FirmwareAnalysisReport:
    """Complete analysis report for VIREON."""
    binary_path: str
    file_size: int
    sha256: str
    vector_table: list[dict] = field(default_factory=list)
    strings: list[dict] = field(default_factory=list)
    regions: list[dict] = field(default_factory=list)
    security_findings: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_json(self, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(asdict(self), f, indent=2)
        print(f"Analysis report: {output_path}")


# ============================================================================
# ARM Cortex-M Known Patterns
# ============================================================================

# Standard ARM Cortex-M exception names for vector table
CORTEX_M_VECTORS = [
    (0, "Initial_SP", "Stack pointer value — security: stack overflow if misconfigured"),
    (1, "Reset", "Reset handler — entry point after boot"),
    (2, "NMI", "Non-maskable interrupt — highest priority, used for safety events"),
    (3, "HardFault", "Hard fault — last resort error handler, SECURITY CRITICAL: fault handler exploitation"),
    (4, "MemManage", "Memory management fault — MPU violation handler"),
    (5, "BusFault", "Bus fault — invalid memory access handler"),
    (6, "UsageFault", "Usage fault — undefined instruction, unaligned access"),
    (7, "Reserved_7", ""),
    (8, "Reserved_8", ""),
    (9, "Reserved_9", ""),
    (10, "Reserved_10", ""),
    (11, "SVCall", "Supervisor call — system service call"),
    (12, "DebugMonitor", "Debug monitor — debug event handler"),
    (13, "Reserved_13", ""),
    (14, "PendSV", "Pendable service — context switching"),
    (15, "SysTick", "System tick — RTOS timer interrupt"),
]

# AES S-box first 16 bytes (partial match is sufficient for identification)
AES_SBOX_START = bytes([
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5,
    0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76
])

# SHA-256 initial hash values (H0-H7)
SHA256_H0 = bytes([
    0x6a, 0x09, 0xe6, 0x67, 0xbb, 0x67, 0xae, 0x85,
    0x3c, 0x6e, 0xf3, 0x72, 0xa5, 0x4f, 0xf5, 0x3a
])

# Security-relevant string patterns
SECURITY_STRING_PATTERNS = {
    "version": [b"v", b"version", b"Version", b"VERSION", b"firmware", b"Firmware"],
    "error": [b"ERROR", b"error", b"fail", b"FAIL", b"overflow", b"OVERFLOW"],
    "safety": [b"SAFETY", b"safety", b"halt", b"HALT", b"violation", b"emergency"],
    "crypto": [b"AES", b"aes", b"SHA", b"sha", b"key", b"KEY", b"encrypt",
               b"decrypt", b"pairing", b"session", b"signature", b"sign"],
    "debug": [b"DEBUG", b"debug", b"printf", b"assert", b"ASSERT"],
}

# Known code region markers in the simulated firmware
REGION_MARKERS = {
    b"AES_SBOX": ("crypto", "critical", "AES S-box lookup table — indicates AES implementation"),
    b"FIR_COEFF": ("dsp", "high", "FIR filter coefficients — DSP engine component"),
    b"SAFETY_MON": ("safety", "critical", "Safety monitor code region"),
    b"CMD_PARSE": ("comms", "critical", "Command parser — primary wireless attack surface"),
    b"CL_CTRL": ("control", "high", "Closed-loop controller — clinical behavior driver"),
}


# ============================================================================
# Firmware Analyzer
# ============================================================================

class FirmwareAnalyzer:
    """VIREON Firmware Analysis Provider.
    
    Performs static analysis of firmware binaries to identify
    security-relevant components, patterns, and potential vulnerabilities.
    
    Design Principle:
        This analyzer works on raw binaries without source code.
        It identifies patterns, not semantics. For VIREON's validation
        framework, this is the first step in firmware security assessment.
    """

    def __init__(self, binary_path: str) -> None:
        self.binary_path = binary_path
        with open(binary_path, 'rb') as f:
            self.data = f.read()
        self.file_size = len(self.data)
        self.sha256 = hashlib.sha256(self.data).hexdigest()
        self.report = FirmwareAnalysisReport(
            binary_path=binary_path,
            file_size=self.file_size,
            sha256=self.sha256,
        )

    def analyze(self, full_analysis: bool = False) -> FirmwareAnalysisReport:
        """Run the complete analysis pipeline."""
        print(f"Analyzing: {self.binary_path}")
        print(f"Size: {self.file_size} bytes, SHA256: {self.sha256[:16]}...")

        # Step 1: Parse vector table
        self._analyze_vector_table()

        # Step 2: Extract strings
        self._extract_strings(min_length=6)

        # Step 3: Identify regions
        self._identify_regions()

        # Step 4: Find cryptographic patterns
        self._find_crypto_patterns()

        # Step 5: Generate security findings
        self._generate_findings()

        if full_analysis:
            # Step 6: Byte frequency analysis (entropy)
            self._entropy_analysis()
            # Step 7: Known byte sequence scan
            self._byte_sequence_scan()

        return self.report

    def _analyze_vector_table(self) -> None:
        """Parse the ARM Cortex-M vector table at offset 0."""
        print("\n[1] Vector Table Analysis")
        entries = []
        n_entries = min(len(self.data) // 4, 16)

        for i in range(n_entries):
            offset = i * 4
            if offset + 4 > len(self.data):
                break
            value = struct.unpack_from('<I', self.data, offset)[0]

            # Map to known vector names
            name = f"IRQ_{i - 16}" if i >= 16 else ""
            security_note = ""
            for idx, vec_name, note in CORTEX_M_VECTORS:
                if idx == i:
                    name = vec_name
                    security_note = note
                    break

            entry = VectorTableEntry(
                index=i, name=name,
                address=value,
                security_note=security_note,
            )
            entries.append(entry)

        self.report.vector_table = [e.to_dict() for e in entries]

        # Print key entries
        for e in entries[:8]:
            sec = f"  [SECURITY: {e.security_note}]" if e.security_note else ""
            print(f"  [{e.index:2d}] 0x{e.address:08X} {e.name}{sec}")

    def _extract_strings(self, min_length: int = 6) -> None:
        """Extract printable ASCII strings from the binary."""
        print(f"\n[2] String Extraction (min length: {min_length})")
        matches = []
        current = bytearray()
        start = 0

        for i, b in enumerate(self.data):
            if 32 <= b < 127:  # Printable ASCII
                if not current:
                    start = i
                current.append(b)
            else:
                if len(current) >= min_length:
                    s = current.decode('ascii', errors='replace')
                    relevance, category = self._classify_string(s)
                    matches.append(StringMatch(
                        offset=start, string=s,
                        security_relevance=relevance,
                        category=category,
                    ))
                current = bytearray()

        # Handle string at end of file
        if len(current) >= min_length:
            s = current.decode('ascii', errors='replace')
            relevance, category = self._classify_string(s)
            matches.append(StringMatch(
                offset=start, string=s,
                security_relevance=relevance,
                category=category,
            ))

        self.report.strings = [m.to_dict() for m in matches]

        # Print security-relevant strings
        sec_strings = [m for m in matches if m.security_relevance in ("critical", "high")]
        print(f"  Total strings: {len(matches)}, Security-relevant: {len(sec_strings)}")
        for m in sec_strings:
            print(f"  [0x{m.offset:04X}] [{m.security_relevance:8s}] ({m.category}): {m.string[:80]}")

    def _classify_string(self, s: str) -> tuple[str, str]:
        """Classify a string's security relevance and category."""
        s_bytes = s.encode('ascii', errors='replace')
        for category, patterns in SECURITY_STRING_PATTERNS.items():
            for pat in patterns:
                if pat in s_bytes:
                    if category == "crypto":
                        return ("critical" if any(kw in s_bytes for kw in [b"key", b"KEY", b"pairing"]) else "high", category)
                    elif category == "safety":
                        return ("critical", category)
                    elif category == "error":
                        return ("high", category)
                    elif category == "debug":
                        return ("medium", category)
                    else:
                        return ("medium", category)
        return ("low", "unknown")

    def _identify_regions(self) -> None:
        """Identify functional regions using known markers."""
        print("\n[3] Region Identification")
        regions = []

        # Find region markers
        for marker, (rtype, sec_rel, annotation) in REGION_MARKERS.items():
            offset = self.data.find(marker)
            if offset >= 0:
                # Estimate region size based on type
                size_map = {
                    "crypto": 272,    # marker(9) + s-box(256) + padding
                    "dsp": 220,       # marker(9) + 51 floats(204) + padding
                    "safety": 80,     # marker(9) + code
                    "comms": 144,    # marker(9) + code
                    "control": 112,   # marker(9) + code
                }
                size = size_map.get(rtype, 64)
                end = min(offset + size, self.file_size)

                region = FirmwareRegion(
                    name=marker.decode('ascii', errors='replace').rstrip('\x00'),
                    start_offset=offset,
                    end_offset=end,
                    size_bytes=end - offset,
                    region_type=rtype,
                    security_relevance=sec_rel,
                    annotations=[annotation],
                )
                regions.append(region)
                print(f"  0x{offset:04X}-0x{end:04X} [{sec_rel:8s}] {region.name}: {annotation}")

        # Vector table region
        regions.insert(0, FirmwareRegion(
            name="VectorTable",
            start_offset=0,
            end_offset=64,
            size_bytes=64,
            region_type="code",
            security_relevance="critical",
            annotations=["ARM Cortex-M vector table — controls all interrupt/exception handling"],
        ))

        self.report.regions = [r.to_dict() for r in regions]

    def _find_crypto_patterns(self) -> None:
        """Search for known cryptographic constants."""
        print("\n[4] Cryptographic Pattern Search")
        findings = self.report.security_findings

        # AES S-box
        aes_offset = self.data.find(AES_SBOX_START)
        if aes_offset >= 0:
            finding = {
                "id": "CRYPTO-001",
                "severity": "critical",
                "type": "cryptographic_component",
                "description": "AES S-box lookup table detected",
                "offset": hex(aes_offset),
                "implication": "AES encryption is used — check key storage, mode of operation, and side-channel resistance",
            }
            findings.append(finding)
            print(f"  [FOUND] AES S-box at offset 0x{aes_offset:04X}")

        # SHA-256
        sha_offset = self.data.find(SHA256_H0)
        if sha_offset >= 0:
            finding = {
                "id": "CRYPTO-002",
                "severity": "high",
                "type": "cryptographic_component",
                "description": "SHA-256 initial hash values detected",
                "offset": hex(sha_offset),
                "implication": "SHA-256 is used — likely for firmware signing or data integrity",
            }
            findings.append(finding)
            print(f"  [FOUND] SHA-256 constants at offset 0x{sha_offset:04X}")

        if not findings:
            print("  No cryptographic patterns detected (may indicate weak or no encryption)")
            self.report.security_findings.append({
                "id": "CRYPTO-003",
                "severity": "high",
                "type": "missing_cryptography",
                "description": "No standard cryptographic constants detected",
                "implication": "Firmware may use no encryption, weak custom crypto, or hardware crypto",
            })

    def _generate_findings(self) -> None:
        """Generate security findings based on analysis."""
        print("\n[5] Security Findings")
        findings = self.report.security_findings

        # Check for debug strings (indicates debug build)
        debug_strings = [s for s in self.report.strings
                         if s.get('category') == 'debug']
        if debug_strings:
            findings.append({
                "id": "BUILD-001",
                "severity": "medium",
                "type": "debug_build",
                "description": f"Debug strings detected ({len(debug_strings)} found)",
                "implication": "Firmware may be a debug build with additional attack surface (debug interfaces, verbose logging)",
            })

        # Check for safety monitor region
        safety_regions = [r for r in self.report.regions
                          if r.get('region_type') == 'safety']
        if safety_regions:
            findings.append({
                "id": "SAFETY-001",
                "severity": "info",
                "type": "safety_monitor_present",
                "description": f"Safety monitor region detected at offset {hex(safety_regions[0]['start_offset'])}",
                "implication": "Safety monitor exists — verify independence from main firmware (VIREON FW-003)",
            })
        else:
            findings.append({
                "id": "SAFETY-002",
                "severity": "critical",
                "type": "no_safety_monitor",
                "description": "No safety monitor region detected",
                "implication": "No independent safety monitoring — firmware compromise directly affects patient safety",
            })

        # Check for error handling strings
        error_strings = [s for s in self.report.strings
                         if s.get('category') == 'error']
        if error_strings:
            findings.append({
                "id": "ERR-001",
                "severity": "medium",
                "type": "error_handling_present",
                "description": f"Error handling strings detected ({len(error_strings)} found)",
                "implication": "Error handling exists — review for information disclosure or fault handler exploitation",
            })

        # Check for crypto key references
        key_strings = [s for s in self.report.strings
                        if 'key' in s.get('string', '').lower() or 'pairing' in s.get('string', '').lower()]
        if key_strings:
            findings.append({
                "id": "KEY-001",
                "severity": "critical",
                "type": "potential_key_material",
                "description": f"Key-related strings detected ({len(key_strings)} found)",
                "details": [s['string'] for s in key_strings],
                "implication": "Strings referencing keys/pairing may indicate hardcoded secrets or key management logic",
            })

        # Recommendations
        self.report.recommendations = [
            "VIREON FW-001: Run command parser fuzzing against the command parser region",
            "VIREON FW-008: Verify secure boot chain covers all firmware regions",
            "VIREON FW-003: Test safety monitor bypass resistance",
            "VIREON FW-004: Verify MPU configuration isolates safety-critical regions",
            "VIREON FW-005: Perform timing analysis on cryptographic operations",
        ]

        for f in findings:
            print(f"  [{f['severity']:8s}] {f['id']}: {f['description']}")
        print(f"\n  Recommendations: {len(self.report.recommendations)}")
        for r in self.report.recommendations:
            print(f"    - {r}")

    def _entropy_analysis(self) -> None:
        """Compute byte entropy for each 256-byte block."""
        print("\n[6] Entropy Analysis")
        import math
        block_size = 256
        high_entropy_blocks = []

        for offset in range(0, self.file_size, block_size):
            block = self.data[offset:offset + block_size]
            if len(block) < 16:
                continue
            freq = [0] * 256
            for b in block:
                freq[b] += 1
            entropy = -sum((c / len(block)) * math.log2(c / len(block))
                           for c in freq if c > 0)
            max_ent = math.log2(256)
            norm_ent = entropy / max_ent if max_ent > 0 else 0

            if norm_ent > 0.8:
                high_entropy_blocks.append((offset, norm_ent))

        if high_entropy_blocks:
            print(f"  High-entropy blocks (>0.8): {len(high_entropy_blocks)}")
            for off, ent in high_entropy_blocks[:5]:
                print(f"    0x{off:04X}: entropy={ent:.3f}")
        else:
            print(f"  No high-entropy blocks detected (simulated binary is mostly structured data)")

    def _byte_sequence_scan(self) -> None:
        """Scan for common ARM instructions and patterns."""
        print("\n[7] ARM Instruction Pattern Scan")
        # Look for common ARM Thumb-2 encodings
        # PUSH {r4-r7, lr} = 0xB5F0
        # POP {r4-r7, pc} = 0xBDF0
        # BX lr = 0x4770
        push_count = 0
        pop_count = 0
        bxlr_count = 0

        for i in range(0, len(self.data) - 1, 2):
            hw = struct.unpack_from('<H', self.data, i)[0]
            if hw == 0xB5F0:
                push_count += 1
            if hw == 0xBDF0:
                pop_count += 1
            if hw == 0x4770:
                bxlr_count += 1

        print(f"  PUSH {{r4-r7,lr}}: {push_count}")
        print(f"  POP  {{r4-r7,pc}}: {pop_count}")
        print(f"  BX   lr: {bxlr_count}")
        if bxlr_count > 0:
            print(f"  → {bxlr_count} potential ROP gadgets (function epilogues)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="VIREON Firmware Reverse Engineering Lab")
    parser.add_argument("--binary", required=True,
                        help="Path to firmware binary")
    parser.add_argument("--full", action="store_true",
                        help="Run full analysis (includes entropy + instruction scan)")
    parser.add_argument("--output_dir", default="./output",
                        help="Output directory")
    args = parser.parse_args()

    if not os.path.exists(args.binary):
        print(f"Error: Binary not found: {args.binary}")
        print("Run Lab 001 first to generate the simulated firmware binary.")
        return

    analyzer = FirmwareAnalyzer(args.binary)
    report = analyzer.analyze(full_analysis=args.full)

    output_path = os.path.join(args.output_dir, "firmware_analysis.json")
    report.to_json(output_path)

    print(f"\n{'='*60}")
    print(f"Analysis Complete")
    print(f"  Findings: {len(report.security_findings)}")
    print(f"  Strings: {len(report.strings)}")
    print(f"  Regions: {len(report.regions)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
