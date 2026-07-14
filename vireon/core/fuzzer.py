import struct
"""
VIREON Protocol Fuzzer — Mutation-based fuzz testing for BCI telemetry frames.

The first BCI-specific protocol fuzzer. Tests the robustness of RFFrameProcessor
against malformed, corrupted, and adversarial telemetry frames.

Strategies:
  - Bit-flip: Random bit mutations in valid frames
  - Truncation: Progressively shorter frames
  - Invalid preamble: Non-0xAA preamble bytes
  - Sequence overflow: Sequence numbers beyond window
  - HMAC corruption: Tampered authentication tags
  - Oversized payload: Frames exceeding expected length
  - Field mutation: Individual field corruption
"""

import random
import time
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone



from vireon.core.protocol import RFFrameProcessor, ProtocolError


@dataclass
class FuzzResult:
    """Result of a single fuzz test case."""
    strategy: str
    test_id: int
    input_hex: str
    input_length: int
    outcome: str          # "REJECTED", "CRASHED", "ACCEPTED" (accepted = potential bug)
    error_message: str
    duration_ms: float
    mutation_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FuzzCampaignReport:
    """Summary report of a full fuzzing campaign."""
    campaign_id: str
    started_at: str
    completed_at: str
    total_iterations: int
    results_by_outcome: Dict[str, int]
    results_by_strategy: Dict[str, Dict[str, int]]
    crashes: List[FuzzResult]
    accepted_anomalies: List[FuzzResult]  # Inputs that should have been rejected but weren't
    coverage_summary: Dict[str, Any]


class ProtocolFuzzer:
    """
    Mutation-based fuzzer for VIREON's RFFrameProcessor.

    Tests both plaintext (CRC-16) and secure (AES-GCM) frame modes.
    """

    STRATEGIES = [
        "bit_flip",
        "truncation",
        "invalid_preamble",
        "seq_overflow",
        "hmac_corruption",
        "oversized_payload",
        "field_mutation",
        "zero_frame",
        "random_bytes",
    ]

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.results: List[FuzzResult] = []
        self.test_counter = 0

    def _make_valid_frame(self, processor: RFFrameProcessor,
                          seq_no: int = 0, secure: bool = False) -> bytes:
        """Generate a known-good frame for mutation."""
        payload = struct.pack(">ff", 12.5, 0.5)  # Dummy telemetry: amplitude, confidence
        return processor.pack_frame(seq_no, payload_type=0x01, payload=payload,
                                    secure_mode=secure)

    def _fuzz_bit_flip(self, frame: bytes, num_flips: int = 1) -> Tuple[bytes, Dict]:
        """Flip random bits in the frame."""
        data = bytearray(frame)
        flipped_positions = []
        for _ in range(num_flips):
            byte_idx = self.rng.randint(0, len(data) - 1)
            bit_idx = self.rng.randint(0, 7)
            data[byte_idx] ^= (1 << bit_idx)
            flipped_positions.append({"byte": byte_idx, "bit": bit_idx})
        return bytes(data), {"flips": flipped_positions}

    def _fuzz_truncation(self, frame: bytes) -> Tuple[bytes, Dict]:
        """Truncate frame to a random shorter length."""
        if len(frame) <= 1:
            return frame, {"truncated_to": len(frame)}
        new_len = self.rng.randint(1, len(frame) - 1)
        return frame[:new_len], {"truncated_to": new_len, "original_len": len(frame)}

    def _fuzz_invalid_preamble(self, frame: bytes) -> Tuple[bytes, Dict]:
        """Replace preamble with non-0xAA byte."""
        data = bytearray(frame)
        invalid = self.rng.choice([0x00, 0xFF, 0xBB, 0xCC, 0xA0, 0x55])
        data[0] = invalid
        return bytes(data), {"original_preamble": "0xAA", "mutated_preamble": f"0x{invalid:02X}"}

    def _fuzz_seq_overflow(self, processor: RFFrameProcessor, secure: bool = False) -> Tuple[bytes, Dict]:
        """Create frame with sequence number far beyond expected window."""
        overflow_seq = processor.expected_seq_no + self.rng.randint(101, 65535)
        payload = struct.pack(">ff", 0.0, 0.0)
        frame = processor.pack_frame(overflow_seq, payload_type=0x01,
                                     payload=payload, secure_mode=secure)
        return frame, {"expected_seq": processor.expected_seq_no, "injected_seq": overflow_seq}

    def _fuzz_hmac_corruption(self, frame: bytes, secure: bool = False) -> Tuple[bytes, Dict]:
        """Corrupt the integrity check (CRC or HMAC tag)."""
        data = bytearray(frame)
        if secure:
            # Corrupt last 16 bytes (AES-GCM tag)
            for i in range(max(0, len(data) - 16), len(data)):
                data[i] ^= 0xFF
            return bytes(data), {"corruption": "AES-GCM tag inverted"}
        else:
            # Corrupt last 2 bytes (CRC-16)
            if len(data) >= 2:
                data[-1] ^= 0xFF
                data[-2] ^= 0xFF
            return bytes(data), {"corruption": "CRC-16 inverted"}

    def _fuzz_oversized_payload(self, processor: RFFrameProcessor,
                                secure: bool = False) -> Tuple[bytes, Dict]:
        """Create frame with payload much larger than expected."""
        size = self.rng.randint(256, 4096)
        payload = bytes(self.rng.getrandbits(8) for _ in range(size))
        
        # Manually construct to bypass pack_frame's struct check
        # PREAMBLE(1) | LEN(1) | SEQ(2) | TYPE(1) | PAYLOAD... | CRC/MAC
        # We'll set length field to 255 or size % 256
        fake_len = size % 256
        header = struct.pack(">BBHB", processor.PREAMBLE, fake_len, processor.expected_seq_no, 0x01)
        frame = bytearray(header + payload)
        
        # Add dummy CRC or MAC
        if secure:
            frame.extend(bytes(16))
        else:
            frame.extend(bytes(2))
            
        return bytes(frame), {"payload_size": size}

    def _fuzz_field_mutation(self, frame: bytes) -> Tuple[bytes, Dict]:
        """Mutate a specific protocol field."""
        data = bytearray(frame)
        if len(data) < 5:
            return bytes(data), {"field": "too_short"}

        field_choice = self.rng.choice(["length", "payload_type", "seq_no"])

        if field_choice == "length":
            # Set length field to wrong value
            data[1] = self.rng.randint(0, 255)
            return bytes(data), {"field": "length", "mutated_to": data[1]}
        elif field_choice == "payload_type":
            data[4] = self.rng.randint(0, 255)
            return bytes(data), {"field": "payload_type", "mutated_to": data[4]}
        elif field_choice == "seq_no":
            new_seq = self.rng.randint(0, 65535)
            struct.pack_into(">H", data, 2, new_seq)
            return bytes(data), {"field": "seq_no", "mutated_to": new_seq}

        return bytes(data), {"field": "none"}

    def _fuzz_zero_frame(self, frame: bytes) -> Tuple[bytes, Dict]:
        """Replace frame with all zeros."""
        return bytes(len(frame)), {"zero_length": len(frame)}

    def _fuzz_random_bytes(self) -> Tuple[bytes, Dict]:
        """Generate completely random bytes."""
        size = self.rng.randint(1, 512)
        data = bytes(self.rng.getrandbits(8) for _ in range(size))
        return data, {"random_size": size}

    def _run_single_test(self, fuzzed_frame: bytes, strategy: str,
                         mutation_details: Dict, secure: bool = False) -> FuzzResult:
        """Execute a single fuzz test case against a fresh processor."""
        self.test_counter += 1
        test_processor = RFFrameProcessor()

        start = time.monotonic()
        try:
            seq, ptype, payload = test_processor.unpack_frame(
                fuzzed_frame, secure_mode=secure, current_time=0.0
            )
            outcome = "ACCEPTED"
            error_msg = f"Frame accepted: seq={seq}, type={ptype}, payload_len={len(payload)}"
        except ProtocolError as e:
            outcome = "REJECTED"
            error_msg = str(e)
        except Exception as e:
            outcome = "CRASHED"
            error_msg = f"{type(e).__name__}: {e}"

        duration = (time.monotonic() - start) * 1000

        result = FuzzResult(
            strategy=strategy,
            test_id=self.test_counter,
            input_hex=fuzzed_frame[:64].hex() + ("..." if len(fuzzed_frame) > 64 else ""),
            input_length=len(fuzzed_frame),
            outcome=outcome,
            error_message=error_msg,
            duration_ms=round(duration, 3),
            mutation_details=mutation_details,
        )
        self.results.append(result)
        return result

    def run_campaign(self, iterations: int = 1000, secure: bool = False,
                     verbose: bool = False) -> FuzzCampaignReport:
        """
        Run a full fuzzing campaign.

        Args:
            iterations: Total number of fuzz test cases to generate.
            secure: Whether to test secure (AES-GCM) mode.
            verbose: Print each test result.

        Returns:
            FuzzCampaignReport with summary statistics.
        """
        self.results = []
        self.test_counter = 0
        started_at = datetime.now(timezone.utc).isoformat()

        # Fresh processor for generating valid base frames
        gen_processor = RFFrameProcessor()

        for i in range(iterations):
            strategy = self.rng.choice(self.STRATEGIES)

            if strategy == "random_bytes":
                fuzzed, details = self._fuzz_random_bytes()
            elif strategy == "seq_overflow":
                fuzzed, details = self._fuzz_seq_overflow(gen_processor, secure)
            elif strategy == "oversized_payload":
                fuzzed, details = self._fuzz_oversized_payload(gen_processor, secure)
            else:
                base_frame = self._make_valid_frame(gen_processor, seq_no=i % 65535, secure=secure)
                if strategy == "bit_flip":
                    num_flips = self.rng.randint(1, 4)
                    fuzzed, details = self._fuzz_bit_flip(base_frame, num_flips)
                elif strategy == "truncation":
                    fuzzed, details = self._fuzz_truncation(base_frame)
                elif strategy == "invalid_preamble":
                    fuzzed, details = self._fuzz_invalid_preamble(base_frame)
                elif strategy == "hmac_corruption":
                    fuzzed, details = self._fuzz_hmac_corruption(base_frame, secure)
                elif strategy == "field_mutation":
                    fuzzed, details = self._fuzz_field_mutation(base_frame)
                elif strategy == "zero_frame":
                    fuzzed, details = self._fuzz_zero_frame(base_frame)
                else:
                    continue

            result = self._run_single_test(fuzzed, strategy, details, secure)

            if verbose:
                icon = {"REJECTED": ".", "CRASHED": "!", "ACCEPTED": "?"}.get(result.outcome, "?")
                print(icon, end="", flush=True)
                if (i + 1) % 80 == 0:
                    print()

        if verbose:
            print()

        completed_at = datetime.now(timezone.utc).isoformat()

        # Compile statistics
        outcomes: Dict[str, int] = {}
        by_strategy: Dict[str, Dict[str, int]] = {}
        crashes = []
        accepted_anomalies = []

        for r in self.results:
            outcomes[r.outcome] = outcomes.get(r.outcome, 0) + 1

            if r.strategy not in by_strategy:
                by_strategy[r.strategy] = {}
            by_strategy[r.strategy][r.outcome] = by_strategy[r.strategy].get(r.outcome, 0) + 1

            if r.outcome == "CRASHED":
                crashes.append(r)
            elif r.outcome == "ACCEPTED":
                accepted_anomalies.append(r)

        return FuzzCampaignReport(
            campaign_id=f"fuzz-{int(time.time())}",
            started_at=started_at,
            completed_at=completed_at,
            total_iterations=len(self.results),
            results_by_outcome=outcomes,
            results_by_strategy=by_strategy,
            crashes=crashes,
            accepted_anomalies=accepted_anomalies,
            coverage_summary={
                "strategies_used": list(by_strategy.keys()),
                "secure_mode": secure,
            },
        )


def print_fuzz_report(report: FuzzCampaignReport) -> None:
    """Print a human-readable fuzzing report."""
    print("=" * 60)
    print(" VIREON Protocol Fuzzer Report")
    print("=" * 60)
    print(f"  Campaign:   {report.campaign_id}")
    print(f"  Started:    {report.started_at}")
    print(f"  Completed:  {report.completed_at}")
    print(f"  Iterations: {report.total_iterations}")
    print(f"  Secure:     {report.coverage_summary.get('secure_mode', False)}")
    print()

    # Outcome summary
    print("  Outcomes:")
    for outcome, count in sorted(report.results_by_outcome.items()):
        pct = 100 * count / max(report.total_iterations, 1)
        icon = {"REJECTED": "✓", "CRASHED": "✗", "ACCEPTED": "⚠"}.get(outcome, "?")
        print(f"    {icon} {outcome:12s} {count:5d} ({pct:.1f}%)")
    print()

    # Per-strategy breakdown
    print("  By Strategy:")
    for strategy, outcomes in sorted(report.results_by_strategy.items()):
        total = sum(outcomes.values())
        crashes = outcomes.get("CRASHED", 0)
        accepted = outcomes.get("ACCEPTED", 0)
        flags = ""
        if crashes > 0:
            flags += f" [!{crashes} CRASH]"
        if accepted > 0:
            flags += f" [?{accepted} ACCEPTED]"
        print(f"    {strategy:25s} {total:5d} tests{flags}")
    print()

    # Critical findings
    if report.crashes:
        print(f"  ⚠ CRASHES FOUND: {len(report.crashes)}")
        for crash in report.crashes[:5]:
            print(f"    Test #{crash.test_id} [{crash.strategy}]: {crash.error_message}")
        if len(report.crashes) > 5:
            print(f"    ... and {len(report.crashes) - 5} more")
        print()

    if report.accepted_anomalies:
        print(f"  ⚠ BYPASS ANOMALIES: {len(report.accepted_anomalies)}")
        for anomaly in report.accepted_anomalies[:5]:
            print(f"    Test #{anomaly.test_id} [{anomaly.strategy}]: {anomaly.error_message}")
        if len(report.accepted_anomalies) > 5:
            print(f"    ... and {len(report.accepted_anomalies) - 5} more")
        print()

    if not report.crashes and not report.accepted_anomalies:
        print("  ✓ No crashes or bypass anomalies detected.")
        print()

    print("=" * 60)


def save_fuzz_report(report: FuzzCampaignReport, output_path: str) -> None:
    """Save fuzz report to JSON."""
    def _serialize(obj):
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report.__dict__, f, indent=2, default=_serialize)


class BrainFlowFuzzer(ProtocolFuzzer):
    """
    Fuzzer for BrainFlow/OpenBCI protocol (Cyton board).
    Generates synthetic 33-byte packets (0xA0 start, 0xC0 end).
    """
    def _make_valid_frame(self, processor: Any, seq_no: int = 0, secure: bool = False) -> bytes:
        # Mock OpenBCI Cyton packet: 33 bytes
        # Byte 0: 0xA0
        # Byte 1: Sample Number
        # Bytes 2-25: EEG Data (24 bytes)
        # Bytes 26-31: Aux Data (6 bytes)
        # Byte 32: 0xC0
        packet = bytearray(33)
        packet[0] = 0xA0
        packet[1] = seq_no % 256
        # Fill EEG/Aux with dummy
        for i in range(2, 32):
            packet[i] = self.rng.randint(0, 255)
        packet[32] = 0xC0
        return bytes(packet)

    def _run_single_test(self, fuzzed_frame: bytes, strategy: str,
                         mutation_details: Dict, secure: bool = False) -> FuzzResult:
        self.test_counter += 1
        start = time.monotonic()
        
        # Simulate OpenBCI parsing check
        outcome = "ACCEPTED"
        error_msg = f"BrainFlow accepted packet of length {len(fuzzed_frame)}"
        
        try:
            if len(fuzzed_frame) != 33:
                raise ValueError("Invalid length")
            if fuzzed_frame[0] != 0xA0 or fuzzed_frame[32] != 0xC0:
                raise ValueError("Invalid start/stop bytes")
        except ValueError as e:
            outcome = "REJECTED"
            error_msg = str(e)
        except Exception as e:
            outcome = "CRASHED"
            error_msg = f"{type(e).__name__}: {e}"

        duration = (time.monotonic() - start) * 1000
        result = FuzzResult(
            strategy=strategy,
            test_id=self.test_counter,
            input_hex=fuzzed_frame[:64].hex() + ("..." if len(fuzzed_frame) > 64 else ""),
            input_length=len(fuzzed_frame),
            outcome=outcome,
            error_message=error_msg,
            duration_ms=round(duration, 3),
            mutation_details=mutation_details,
        )
        self.results.append(result)
        return result
