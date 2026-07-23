"""
VIREON-LABS NL-003 Lab 001: Simulated IPG Firmware
==================================================

Simulates the firmware of an implantable pulse generator (IPG) with
security instrumentation. Implements: secure boot chain, RTOS task
scheduler, DSP pipeline, closed-loop controller, safety monitor,
stimulation pulse generator, and command parser — all in Python with
security event logging.

Learning Objectives:
    1. Understand the structure and interaction of IPG firmware subsystems
    2. Observe how firmware vulnerabilities manifest in device behavior
    3. Test the safety monitor's ability to detect parameter violations
    4. Explore the secure boot chain and OTA update mechanisms
    5. Generate firmware analysis artifacts for VIREON validation

Required Software: Python 3.9+, numpy, matplotlib
Required Hardware: None
Estimated Time: 4-5 hours
Difficulty: Intermediate-Advanced

Usage:
    python firmware_simulator.py --mode demo --duration 10
    python firmware_simulator.py --mode exploit_test
    python firmware_simulator.py --mode ota_test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Optional

import numpy as np


class SecurityEventType(Enum):
    BOOT_START = auto()
    BOOT_VERIFIED = auto()
    BOOT_FAILED = auto()
    COMMAND_RECEIVED = auto()
    COMMAND_ACCEPTED = auto()
    COMMAND_REJECTED = auto()
    PARAMETER_CHANGE = auto()
    SAFETY_VIOLATION = auto()
    SAFETY_HALT = auto()
    OTA_START = auto()
    OTA_CHUNK_RECEIVED = auto()
    OTA_COMPLETE = auto()
    OTA_VERIFIED = auto()
    OTA_REJECTED = auto()
    BUFFER_OVERFLOW = auto()
    WATCHDOG_RESET = auto()
    FAULT_DETECTED = auto()


@dataclass
class SecurityEvent:
    timestamp_ms: float
    event_type: SecurityEventType
    source: str
    details: dict = field(default_factory=dict)
    severity: str = "info"  # info, warning, critical

    def to_dict(self) -> dict:
        return {
            "timestamp_ms": self.timestamp_ms,
            "event_type": self.event_type.name,
            "source": self.source,
            "details": self.details,
            "severity": self.severity,
        }


class SecurityLogger:
    """Records all security-relevant events for VIREON analysis."""
    def __init__(self) -> None:
        self.events: list[SecurityEvent] = []

    def log(self, event_type: SecurityEventType, source: str,
            details: Optional[dict] = None, severity: str = "info") -> None:
        self.events.append(SecurityEvent(
            timestamp_ms=time.time() * 1000,
            event_type=event_type,
            source=source,
            details=details or {},
            severity=severity,
        ))

    def get_critical_events(self) -> list[SecurityEvent]:
        return [e for e in self.events if e.severity == "critical"]

    def summary(self) -> str:
        lines = [f"Security Events: {len(self.events)} total"]
        by_type = {}
        for e in self.events:
            by_type[e.event_type.name] = by_type.get(e.event_type.name, 0) + 1
        for t, c in sorted(by_type.items()):
            lines.append(f"  {t}: {c}")
        return "\n".join(lines)


@dataclass
class StimParameters:
    """Stimulation parameters with safety limits."""
    amplitude_ma: float = 2.0      # 0-10 mA
    pulse_width_us: float = 90.0  # 60-500 us
    frequency_hz: float = 130.0   # 1-200 Hz
    electrode_config: int = 0     # 0-15 (4 electrodes, bipolar)

    # Absolute safety limits
    MAX_AMPLITUDE = 10.0
    MAX_PULSE_WIDTH = 500.0
    MAX_FREQUENCY = 200.0

    def validate(self) -> list[str]:
        """Returns list of safety violations."""
        violations = []
        if self.amplitude_ma > self.MAX_AMPLITUDE:
            violations.append(f"amplitude {self.amplitude_ma:.1f} > {self.MAX_AMPLITUDE}")
        if self.pulse_width_us > self.MAX_PULSE_WIDTH:
            violations.append(f"pulse_width {self.pulse_width_us:.0f} > {self.MAX_PULSE_WIDTH:.0f}")
        if self.frequency_hz > self.MAX_FREQUENCY:
            violations.append(f"frequency {self.frequency_hz:.0f} > {self.MAX_FREQUENCY:.0f}")
        return violations

    def to_register_map(self) -> dict:
        """Simulates memory-mapped stimulation registers."""
        return {
            "STIM_CTRL": 0x01 if self.amplitude_ma > 0 else 0x00,
            "STIM_AMPLITUDE": int(self.amplitude_ma * 1000),  # uA
            "STIM_PW_CATH": int(self.pulse_width_us),
            "STIM_PW_ANOD": int(self.pulse_width_us * 1.1),  # 110% charge balance
            "STIM_FREQ": int(self.frequency_hz),
            "STIM_ELECTRODE": self.electrode_config,
            "STIM_STATUS": 0x00,
        }


class SafetyMonitor:
    """Independent safety monitor with shadow parameter checking.
    
    Security Note:
        In a real device, this would run as a separate RTOS task or
        on a separate core. Here it runs as a separate Python object
        to simulate independence.
    """
    def __init__(self, logger: SecurityLogger, config: Optional[dict] = None) -> None:
        self.logger = logger
        self.config = config or {}
        self.shadow_params = StimParameters()
        self.violation_count = 0
        self.halted = False
        self.check_interval_ms = self.config.get("check_interval_ms", 1.0)
        self.enabled = True

    def check_parameters(self, actual: StimParameters) -> bool:
        """Compare actual parameters against safety limits."""
        violations = actual.validate()
        if violations:
            self.violation_count += 1
            self.logger.log(
                SecurityEventType.SAFETY_VIOLATION,
                "SafetyMonitor",
                {"violations": violations, "params": asdict(actual)},
                severity="critical",
            )
            if self.violation_count >= 3:
                self.halt()
            return False
        return True

    def check_charge_balance(self, cathodic_us: float, anodic_us: float) -> bool:
        """Verify charge balance (anodic >= cathodic)."""
        if anodic_us < cathodic_us:
            self.logger.log(
                SecurityEventType.SAFETY_VIOLATION,
                "SafetyMonitor",
                {"type": "charge_imbalance", "cathodic": cathodic_us, "anodic": anodic_us},
                severity="critical",
            )
            return False
        return True

    def halt(self) -> None:
        """Emergency halt — disable all stimulation."""
        self.halted = True
        self.logger.log(
            SecurityEventType.SAFETY_HALT,
            "SafetyMonitor",
            {"reason": "violation_threshold_exceeded", "total_violations": self.violation_count},
            severity="critical",
        )

    def reset(self) -> None:
        self.violation_count = 0
        self.halted = False


class ClosedLoopController:
    """PI controller for adaptive DBS (simplified).
    
    Security Note:
        The controller's parameters (gains, setpoint, integral state)
        are security-critical. Modification of any of these changes
        the device's clinical behavior.
    """
    def __init__(self, logger: SecurityLogger) -> None:
        self.logger = logger
        self.setpoint = 50.0    # Target beta band power (arbitrary units)
        self.kp = 0.5         # Proportional gain
        self.ki = 0.05        # Integral gain
        self.integral = 0.0   # Integral state
        self.integral_max = 200.0
        self.output_min = 0.0
        self.output_max = 7.0
        self.enabled = False

    def update(self, beta_power: float, dt: float = 0.01) -> float:
        """Compute control output from current beta power."""
        if not self.enabled:
            return 0.0
        
        error = self.setpoint - beta_power
        self.integral += error * dt
        # Anti-windup
        self.integral = np.clip(self.integral, -self.integral_max, self.integral_max)
        output = self.kp * error + self.ki * self.integral
        output = np.clip(output, self.output_min, self.output_max)
        return float(output)


class CommandParser:
    """Wireless command parser with security vulnerabilities (for learning).
    
    Security Note:
        This parser contains INTENTIONAL vulnerabilities that
        correspond to real-world firmware vulnerabilities:
        - Fixed-size buffer without bounds checking (line overflow)
        - Insufficient parameter validation
        - No per-command authorization
        These are documented and used in Lab 002 for analysis.
    """
    def __init__(self, logger: SecurityLogger, stim: StimParameters,
                 controller: ClosedLoopController,
                 vulnerable_mode: bool = True) -> None:
        self.logger = logger
        self.stim = stim
        self.controller = controller
        self.vulnerable_mode = vulnerable_mode
        self.command_buffer = bytearray(256)  # Fixed 256-byte buffer
        self.buffer_pos = 0
        self.authorized_commands = [
            "GET_STATUS", "SET_AMPLITUDE", "SET_FREQUENCY",
            "SET_PULSE_WIDTH", "ENABLE_CL", "DISABLE_CL",
            "GET_DIAGNOSTICS", "START_THERAPY", "STOP_THERAPY",
        ]

    def parse(self, raw_packet: bytes) -> Optional[dict]:
        """Parse a raw wireless packet into a command.
        
        Returns parsed command dict or None if invalid.
        """
        self.logger.log(
            SecurityEventType.COMMAND_RECEIVED,
            "CommandParser",
            {"packet_size": len(raw_packet)},
        )

        if len(raw_packet) < 4:
            self.logger.log(
                SecurityEventType.COMMAND_REJECTED,
                "CommandParser",
                {"reason": "packet_too_short", "length": len(raw_packet)},
            )
            return None

        # Parse header
        cmd_type = raw_packet[0]
        seq_num = struct.unpack_from(">H", raw_packet, 1)[0]
        payload = raw_packet[3:]

        # VULNERABILITY: Copy to fixed buffer without bounds check
        if self.vulnerable_mode:
            try:
                self.command_buffer[self.buffer_pos:self.buffer_pos + len(payload)] = payload
                self.buffer_pos += len(payload)
            except IndexError:
                self.logger.log(
                    SecurityEventType.BUFFER_OVERFLOW,
                    "CommandParser",
                    {"buffer_pos": self.buffer_pos, "payload_len": len(payload)},
                    severity="critical",
                )
                self.buffer_pos = 0  # Reset
        else:
            if self.buffer_pos + len(payload) > len(self.command_buffer):
                self.logger.log(
                    SecurityEventType.COMMAND_REJECTED,
                    "CommandParser",
                    {"reason": "buffer_would_overflow"},
                )
                return None
            self.command_buffer[self.buffer_pos:self.buffer_pos + len(payload)] = payload
            self.buffer_pos += len(payload)

        # Parse command
        cmd = None
        if cmd_type == 0x01:  # SET_AMPLITUDE
            if len(payload) >= 4:
                amp = struct.unpack_from(">f", payload, 0)[0]
                cmd = {"type": "SET_AMPLITUDE", "value": amp}
        elif cmd_type == 0x02:  # SET_FREQUENCY
            if len(payload) >= 4:
                freq = struct.unpack_from(">f", payload, 0)[0]
                cmd = {"type": "SET_FREQUENCY", "value": freq}
        elif cmd_type == 0x03:  # ENABLE_CL
            cmd = {"type": "ENABLE_CL"}
        elif cmd_type == 0x04:  # DISABLE_CL
            cmd = {"type": "DISABLE_CL"}
        elif cmd_type == 0x05:  # SET_CONTROLLER_GAINS (DANGEROUS)
            if len(payload) >= 8:
                kp = struct.unpack_from(">f", payload, 0)[0]
                ki = struct.unpack_from(">f", payload, 4)[0]
                cmd = {"type": "SET_CONTROLLER_GAINS", "kp": kp, "ki": ki}
        elif cmd_type == 0x06:  # SET_SETPOINT (DANGEROUS)
            if len(payload) >= 4:
                sp = struct.unpack_from(">f", payload, 0)[0]
                cmd = {"type": "SET_SETPOINT", "value": sp}
        else:
            self.logger.log(
                SecurityEventType.COMMAND_REJECTED,
                "CommandParser",
                {"reason": "unknown_command_type", "cmd_type": hex(cmd_type)},
            )
            return None

        if cmd:
            self.logger.log(
                SecurityEventType.COMMAND_ACCEPTED,
                "CommandParser",
                {"command": cmd},
            )
        return cmd

    def execute(self, cmd: dict, safety: SafetyMonitor) -> bool:
        """Execute a parsed command. Returns True if executed."""
        if safety.halted and cmd["type"] not in ["GET_STATUS", "GET_DIAGNOSTICS"]:
            self.logger.log(
                SecurityEventType.COMMAND_REJECTED,
                "CommandParser",
                {"reason": "device_halted"},
                severity="critical",
            )
            return False

        cmd_type = cmd["type"]

        if cmd_type == "SET_AMPLITUDE":
            # VULNERABILITY: insufficient upper bound check in vulnerable mode
            if self.vulnerable_mode:
                self.stim.amplitude_ma = cmd["value"]
            else:
                if cmd["value"] < 0 or cmd["value"] > StimParameters.MAX_AMPLITUDE:
                    self.logger.log(
                        SecurityEventType.COMMAND_REJECTED,
                        "CommandParser",
                        {"reason": "amplitude_out_of_range", "value": cmd["value"]},
                    )
                    return False
                self.stim.amplitude_ma = cmd["value"]
            self.logger.log(
                SecurityEventType.PARAMETER_CHANGE,
                "CommandParser",
                {"parameter": "amplitude_ma", "new_value": self.stim.amplitude_ma},
            )

        elif cmd_type == "SET_FREQUENCY":
            self.stim.frequency_hz = cmd["value"]
            self.logger.log(
                SecurityEventType.PARAMETER_CHANGE,
                "CommandParser",
                {"parameter": "frequency_hz", "new_value": self.stim.frequency_hz},
            )

        elif cmd_type == "ENABLE_CL":
            self.controller.enabled = True

        elif cmd_type == "DISABLE_CL":
            self.controller.enabled = False

        elif cmd_type == "SET_CONTROLLER_GAINS":
            # VULNERABILITY: allows arbitrary gain modification
            self.controller.kp = cmd["kp"]
            self.controller.ki = cmd["ki"]
            self.logger.log(
                SecurityEventType.PARAMETER_CHANGE,
                "CommandParser",
                {"parameter": "controller_gains",
                 "kp": cmd["kp"], "ki": cmd["ki"]},
                severity="warning",
            )

        elif cmd_type == "SET_SETPOINT":
            # VULNERABILITY: allows arbitrary setpoint
            self.controller.setpoint = cmd["value"]
            self.logger.log(
                SecurityEventType.PARAMETER_CHANGE,
                "CommandParser",
                {"parameter": "setpoint", "new_value": cmd["value"]},
                severity="warning",
            )

        return True


class SecureBoot:
    """Simulated secure boot chain.
    
    Security Note:
        Simulates the ROM → Flash Bootloader → Application chain
        with hash verification, signature verification, and version check.
    """
    def __init__(self, logger: SecurityLogger) -> None:
        self.logger = logger
        self.rom_hash = self._compute_firmware_hash("ROM_BOOTLOADER_v1.0.0")
        self.rom_stored_hash = self.rom_hash  # In real device: OTP-fused
        self.current_version = 3
        self.monotonic_counter = 3  # Stored in OTP

    def _compute_firmware_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def verify_boot_chain(self, firmware_content: str,
                          firmware_signature: Optional[str] = None,
                          firmware_version: int = 0) -> bool:
        """Verify the complete boot chain."""
        self.logger.log(SecurityEventType.BOOT_START, "SecureBoot", {})

        # Stage 0: Verify ROM bootloader
        if self.rom_hash != self.rom_stored_hash:
            self.logger.log(
                SecurityEventType.BOOT_FAILED, "SecureBoot",
                {"stage": 0, "reason": "ROM_hash_mismatch"},
                severity="critical",
            )
            return False
        self.logger.log(SecurityEventType.BOOT_VERIFIED, "SecureBoot", {"stage": 0})

        # Stage 1: Verify application firmware hash
        fw_hash = self._compute_firmware_hash(firmware_content)
        if firmware_signature is not None:
            # Simplified: signature = hash (in reality: ECDSA verification)
            if firmware_signature != fw_hash:
                self.logger.log(
                    SecurityEventType.BOOT_FAILED, "SecureBoot",
                    {"stage": 1, "reason": "signature_mismatch"},
                    severity="critical",
                )
                return False
        else:
            # No signature provided — reject
            self.logger.log(
                SecurityEventType.BOOT_FAILED, "SecureBoot",
                {"stage": 1, "reason": "missing_signature"},
                severity="critical",
            )
            return False
        self.logger.log(SecurityEventType.BOOT_VERIFIED, "SecureBoot", {"stage": 1})

        # Stage 2: Version check (anti-rollback)
        if firmware_version < self.monotonic_counter:
            self.logger.log(
                SecurityEventType.BOOT_FAILED, "SecureBoot",
                {"stage": 2, "reason": "version_rollback",
                 "firmware_version": firmware_version,
                 "min_version": self.monotonic_counter},
                severity="critical",
            )
            return False
        self.logger.log(SecurityEventType.BOOT_VERIFIED, "SecureBoot", {"stage": 2})

        if firmware_version > self.monotonic_counter:
            self.monotonic_counter = firmware_version

        self.current_version = firmware_version
        return True


class FirmwareSimulator:
    """Complete simulated IPG firmware system.
    
    VIREON Integration:
        This simulator is structured as a VIREON digital twin
        component that executes a simplified model of IPG firmware.
    """
    def __init__(self, config: Optional[dict] = None) -> None:
        self.config = config or {}
        self.logger = SecurityLogger()
        self.stim = StimParameters()
        self.safety = SafetyMonitor(self.logger, config)
        self.controller = ClosedLoopController(self.logger)
        self.parser = CommandParser(
            self.logger, self.stim, self.controller,
            vulnerable_mode=self.config.get("vulnerable_mode", True),
        )
        self.boot = SecureBoot(self.logger)
        self.tick_count = 0
        self.device_time_ms = 0.0
        self.tick_interval_ms = 4.0  # 250 Hz

    def boot_device(self, firmware_content: str = "FIRMWARE_v3.0.0",
                    signature: Optional[str] = None,
                    version: int = 3) -> bool:
        """Execute the secure boot chain."""
        if signature is None:
            signature = self.boot._compute_firmware_hash(firmware_content)
        return self.boot.verify_boot_chain(firmware_content, signature, version)

    def tick(self, beta_power: float = 50.0) -> dict:
        """Execute one firmware tick (4 ms at 250 Hz).
        
        Simulates: safety check, closed-loop update, stimulation output.
        """
        self.tick_count += 1
        self.device_time_ms += self.tick_interval_ms

        # Safety monitor check (every tick)
        safe = self.safety.check_parameters(self.stim)
        if not safe and self.safety.halted:
            return {
                "tick": self.tick_count,
                "time_ms": self.device_time_ms,
                "stimulation_active": False,
                "safety_halted": True,
                "controller_output": 0.0,
            }

        # Closed-loop update (every 10th tick = 25 Hz control rate)
        ctrl_output = 0.0
        if self.tick_count % 10 == 0 and self.controller.enabled:
            ctrl_output = self.controller.update(beta_power, dt=self.tick_interval_ms * 10 / 1000)
            if self.controller.enabled:
                self.stim.amplitude_ma = ctrl_output

        # Stimulation output
        stim_active = self.stim.amplitude_ma > 0 and not self.safety.halted

        return {
            "tick": self.tick_count,
            "time_ms": self.device_time_ms,
            "stimulation_active": stim_active,
            "safety_halted": self.safety.halted,
            "controller_output": ctrl_output,
            "amplitude_ma": self.stim.amplitude_ma,
            "frequency_hz": self.stim.frequency_hz,
        }

    def process_command(self, raw_packet: bytes) -> Optional[dict]:
        """Process a wireless command through the full pipeline."""
        cmd = self.parser.parse(raw_packet)
        if cmd is None:
            return None
        success = self.parser.execute(cmd, self.safety)
        return {"command": cmd, "executed": success}

    def run_simulation(self, duration_s: float = 10.0,
                       beta_power_series: Optional[np.ndarray] = None,
                       commands: Optional[list[bytes]] = None) -> dict:
        """Run a complete simulation with optional command injection.
        
        Returns simulation results and security report.
        """
        n_ticks = int(duration_s * 1000 / self.tick_interval_ms)
        results = []

        if beta_power_series is None:
            rng = np.random.default_rng(self.config.get("seed", 42))
            beta_power_series = 50.0 + 10.0 * rng.standard_normal(n_ticks)
            # Add some slow drift
            beta_power_series += 5.0 * np.sin(2 * np.pi * 0.1 * np.arange(n_ticks) * self.tick_interval_ms / 1000)

        command_idx = 0
        for t in range(n_ticks):
            # Process commands at scheduled ticks
            if commands and command_idx < len(commands):
                if t == int(commands[command_idx][0] / self.tick_interval_ms) if isinstance(commands[command_idx], tuple) else t % 250 == 0:
                    if isinstance(commands[command_idx], tuple):
                        _, pkt = commands[command_idx]
                    else:
                        pkt = commands[command_idx]
                    self.process_command(pkt)
                    command_idx += 1

            bp = float(beta_power_series[min(t, len(beta_power_series) - 1)])
            tick_result = self.tick(bp)
            results.append(tick_result)

        return {
            "n_ticks": n_ticks,
            "duration_s": duration_s,
            "safety_halted": self.safety.halted,
            "final_amplitude": self.stim.amplitude_ma,
            "safety_violations": self.safety.violation_count,
            "security_events": len(self.logger.events),
            "tick_results": results,
        }

    def export_report(self, output_dir: str = "./output") -> None:
        """Export security report and firmware analysis artifacts."""
        os.makedirs(output_dir, exist_ok=True)

        report = {
            "firmware_config": self.config,
            "stim_parameters": asdict(self.stim),
            "controller_state": {
                "enabled": self.controller.enabled,
                "setpoint": self.controller.setpoint,
                "kp": self.controller.kp,
                "ki": self.controller.ki,
                "integral": self.controller.integral,
            },
            "safety_monitor": {
                "halted": self.safety.halted,
                "violations": self.safety.violation_count,
                "enabled": self.safety.enabled,
            },
            "boot_state": {
                "current_version": self.boot.current_version,
                "monotonic_counter": self.boot.monotonic_counter,
            },
            "register_map": self.stim.to_register_map(),
            "security_events": [e.to_dict() for e in self.logger.events],
            "security_summary": {
                "total_events": len(self.logger.events),
                "critical_events": len(self.logger.get_critical_events()),
            },
        }

        report_path = os.path.join(output_dir, "firmware_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Report exported: {report_path}")

        # Export simulated firmware binary for Lab 002
        self._export_simulated_binary(output_dir)

    def _export_simulated_binary(self, output_dir: str) -> None:
        """Generate a simulated firmware binary file for reverse engineering."""
        # Build a realistic-ish ARM binary structure
        binary = bytearray()

        # Vector table (16 entries x 4 bytes = 64 bytes)
        # Initial SP, Reset handler, NMI, HardFault, MemManage, BusFault, UsageFault, ...
        binary += struct.pack("<I", 0x20008000)  # Initial SP
        binary += struct.pack("<I", 0x08000100)  # Reset handler
        binary += struct.pack("<I", 0x08000200)  # NMI handler
        binary += struct.pack("<I", 0x08000300)  # HardFault handler
        for _ in range(12):
            binary += struct.pack("<I", 0x08000000 + 0x100 * (4 + _))

        # Padding to code area
        while len(binary) < 256:
            binary += b"\x00"

        # Simulated code region with identifiable patterns
        # "AES_SBOX" marker + 256-byte S-box
        sbox_start = len(binary)
        binary += b"AES_SBOX\x00"
        # Simplified AES S-box (first 16 bytes of real S-box)
        aes_sbox = bytes([0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5,
                           0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76])
        binary += aes_sbox * 16  # Pad to 256 bytes

        # "FIR_COEFF" marker + filter coefficients
        binary += b"FIR_COEFF\x00"
        n_coeffs = 51
        coeffs = np.zeros(n_coeffs, dtype=np.float32)
        coeffs[n_coeffs // 2] = 1.0  # Identity filter (simplified)
        binary += coeffs.tobytes()

        # "SAFETY_MON" marker
        binary += b"SAFETY_MON\x00"
        binary += b"\x01" * 64  # Safety monitor code region

        # "CMD_PARSE" marker
        binary += b"CMD_PARSE\x00"
        binary += b"\x02" * 128  # Command parser code region

        # "CL_CTRL" marker
        binary += b"CL_CTRL\x00"
        binary += b"\x03" * 96  # Closed-loop controller code region

        # Strings section
        binary += b"VIREON IPG Firmware v3.0.0\x00"
        binary += b"ERROR: Buffer overflow in command parser\x00"
        binary += b"WARNING: Parameter out of range\x00"
        binary += b"SAFETY: Stimulation halted\x00"
        binary += b"Pairing secret: %s\x00"
        binary += b"Session key derived\x00"

        bin_path = os.path.join(output_dir, "simulated_firmware.bin")
        with open(bin_path, "wb") as f:
            f.write(binary)
        print(f"Simulated binary exported: {bin_path}")


def make_set_amplitude_packet(amplitude: float) -> bytes:
    """Create a SET_AMPLITUDE command packet."""
    header = bytes([0x01, 0x00, 0x01])  # cmd_type=SET_AMPLITUDE, seq=1
    payload = struct.pack(">f", amplitude)
    return header + payload


def make_set_frequency_packet(frequency: float) -> bytes:
    header = bytes([0x02, 0x00, 0x02])
    payload = struct.pack(">f", frequency)
    return header + payload


def make_enable_cl_packet() -> bytes:
    return bytes([0x03, 0x00, 0x03, 0x00])  # 4-byte header + empty payload


def make_set_gains_packet(kp: float, ki: float) -> bytes:
    header = bytes([0x05, 0x00, 0x04])
    payload = struct.pack(">ff", kp, ki)
    return header + payload


def make_set_setpoint_packet(sp: float) -> bytes:
    header = bytes([0x06, 0x00, 0x05])
    payload = struct.pack(">f", sp)
    return header + payload


def demo_mode(sim: FirmwareSimulator) -> None:
    """Run normal operation demo."""
    print("\n" + "=" * 60)
    print("VIREON Firmware Simulator: Normal Operation Demo")
    print("=" * 60)

    # Boot
    print("\n--- Boot Sequence ---")
    success = sim.boot_device()
    print(f"Boot result: {'PASS' if success else 'FAIL'}")

    # Process some commands
    print("\n--- Command Processing ---")
    cmds = [
        ("SET_AMPLITUDE 3.0 mA", make_set_amplitude_packet(3.0)),
        ("ENABLE_CL", make_enable_cl_packet()),
        ("SET_SETPOINT 40.0", make_set_setpoint_packet(40.0)),
    ]
    for name, pkt in cmds:
        result = sim.process_command(pkt)
        if result:
            print(f"  {name}: {'OK' if result['executed'] else 'REJECTED'}")
        else:
            print(f"  {name}: PARSE ERROR")

    # Run simulation
    print("\n--- 10-Second Simulation ---")
    result = sim.run_simulation(duration_s=10.0)
    print(f"  Ticks: {result['n_ticks']}")
    print(f"  Safety halted: {result['safety_halted']}")
    print(f"  Safety violations: {result['safety_violations']}")
    print(f"  Final amplitude: {result['final_amplitude']:.3f} mA")
    print(f"  Security events: {result['security_events']}")

    sim.export_report()
    print(f"\n{sim.logger.summary()}")


def exploit_test_mode(sim: FirmwareSimulator) -> None:
    """Demonstrate firmware vulnerabilities."""
    print("\n" + "=" * 60)
    print("VIREON Firmware Simulator: Exploit Demonstration")
    print("=" * 60)

    sim.boot_device()

    # Exploit 1: Excessive amplitude (bypasses safety in vulnerable mode)
    print("\n--- Exploit 1: Excessive Stimulation Amplitude ---")
    sim.process_command(make_set_amplitude_packet(15.0))  # 15 mA > 10 mA limit
    print(f"  Current amplitude: {sim.stim.amplitude_ma:.1f} mA (limit: {StimParameters.MAX_AMPLITUDE})")
    print(f"  Safety monitor: violations={sim.safety.violation_count}, halted={sim.safety.halted}")

    # Exploit 2: Controller setpoint manipulation
    print("\n--- Exploit 2: Controller Setpoint Manipulation ---")
    sim.safety.reset()
    sim.process_command(make_enable_cl_packet())
    sim.process_command(make_set_setpoint_packet(0.0))  # Setpoint = 0 → max stimulation
    print(f"  Setpoint: {sim.controller.setpoint} (was 50.0)")
    print(f"  Controller enabled: {sim.controller.enabled}")

    # Exploit 3: Gain manipulation
    print("\n--- Exploit 3: Controller Gain Manipulation ---")
    sim.process_command(make_set_gains_packet(kp=10.0, ki=1.0))  # Aggressive gains
    print(f"  Kp: {sim.controller.kp} (was 0.5)")
    print(f"  Ki: {sim.controller.ki} (was 0.05)")

    # Run with manipulated controller
    print("\n--- Simulation with Manipulated Controller ---")
    result = sim.run_simulation(duration_s=5.0)
    print(f"  Final amplitude: {result['final_amplitude']:.3f} mA")
    print(f"  Safety halted: {result['safety_halted']}")
    print(f"  Critical security events: {len(sim.logger.get_critical_events())}")

    sim.export_report()
    print(f"\n{sim.logger.summary()}")


def ota_test_mode(sim: FirmwareSimulator) -> None:
    """Demonstrate OTA update security."""
    print("\n" + "=" * 60)
    print("VIREON Firmware Simulator: OTA Update Security Test")
    print("=" * 60)

    # Test 1: Legitimate update
    print("\n--- Test 1: Legitimate Update (v3 → v4) ---")
    new_fw = "FIRMWARE_v4.0.0"
    sig = sim.boot._compute_firmware_hash(new_fw)
    result = sim.boot.verify_boot_chain(new_fw, sig, firmware_version=4)
    print(f"  Result: {'PASS' if result else 'FAIL'}")
    print(f"  Monotonic counter: {sim.boot.monotonic_counter}")

    # Test 2: Tampered firmware
    print("\n--- Test 2: Tampered Firmware (bad signature) ---")
    tampered = "FIRMWARE_v4.0.0_TAMPERED"
    bad_sig = "deadbeef"
    result = sim.boot.verify_boot_chain(tampered, bad_sig, firmware_version=5)
    print(f"  Result: {'PASS' if result else 'FAIL (expected)'}")

    # Test 3: Downgrade attack
    print("\n--- Test 3: Downgrade Attack (v4 → v2) ---")
    old_fw = "FIRMWARE_v2.0.0"
    old_sig = sim.boot._compute_firmware_hash(old_fw)
    result = sim.boot.verify_boot_chain(old_fw, old_sig, firmware_version=2)
    print(f"  Result: {'PASS' if result else 'FAIL (expected — rollback blocked)'}")

    # Test 4: Missing signature
    print("\n--- Test 4: Missing Signature ---")
    result = sim.boot.verify_boot_chain(new_fw, None, firmware_version=6)
    print(f"  Result: {'PASS' if result else 'FAIL (expected — no signature)'}")

    sim.export_report()


def main() -> None:
    parser = argparse.ArgumentParser(description="VIREON IPG Firmware Simulator")
    parser.add_argument("--mode", choices=["demo", "exploit_test", "ota_test"],
                        default="demo", help="Simulation mode")
    parser.add_argument("--duration", type=float, default=10.0,
                        help="Simulation duration in seconds")
    parser.add_argument("--vulnerable", action="store_true", default=True,
                        help="Enable vulnerable mode (default: True)")
    parser.add_argument("--secure", action="store_true",
                        help="Disable vulnerable mode (secure firmware)")
    parser.add_argument("--output_dir", default="./output",
                        help="Output directory for reports")
    args = parser.parse_args()

    config = {
        "vulnerable_mode": not args.secure,
        "seed": 42,
    }
    sim = FirmwareSimulator(config)

    if args.mode == "demo":
        demo_mode(sim)
    elif args.mode == "exploit_test":
        exploit_test_mode(sim)
    elif args.mode == "ota_test":
        ota_test_mode(sim)

    sim.export_report(args.output_dir)


if __name__ == "__main__":
    main()
