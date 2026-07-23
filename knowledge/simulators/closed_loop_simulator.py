#!/usr/bin/env python3
"""
VIREON NL-005 Lab 001: Closed-Loop Neurostimulator Simulator
=============================================================
Simulates a closed-loop DBS system for Parkinson's disease:
  - Neural signal model (beta-band LFP generation)
  - Sensing pipeline (ADC simulation with noise)
  - DSP processing (bandpower feature extraction)
  - PI controller with anti-windup and rate limiting
   - Stimulation actuation with charge balance
  - Safety monitor (multi-level anomaly detection)
  - Energy model (battery tracking)
  - Security event logging

Modes:
  demo        — Short 200-cycle demo with console output
  normal      — Full 1000-cycle run, outputs JSON
  attack_test — 1000-cycle run with injected vulnerabilities for Lab 002

Usage:
  python closed_loop_simulator.py --mode demo
  python closed_loop_simulator.py --mode normal --num_cycles 2000 --output_dir output
  python closed_loop_simulator.py --mode attack_test --output_dir output
"""

import argparse
import json
import math
import os
import random
import struct
import sys
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple


# ============================================================================
# Constants
# ============================================================================

# Neural signal model
BETA_FREQ_LO = 13.0       # Hz
BETA_FREQ_HI = 30.0       # Hz
DOMINANT_BETA_FREQ = 20.0 # Hz (Parkinson's STN typical)
SIGNAL_NOISE_STD = 0.5     # uV (sensor noise)
AMPLITUDE_VARIABILITY = 0.15  # 15% natural amplitude variation

# Stimulation response model (first-order)
PLANT_GAIN = 1.0          # Normalized coupling: stim -> beta suppression
PLANT_TAU = 0.2           # seconds (neural response time constant)
STIM_COUPLING_K = 0.12    # How strongly stimulation suppresses beta amplitude

# PI controller defaults
DEFAULT_KP = 0.05
DEFAULT_KI = 0.005
DEFAULT_SETPOINT = 0.0    # dB (target beta power relative to baseline)
INTEGRAL_LIMIT = 50.0     # Anti-windup integral bound
RATE_LIMIT = 0.1          # mA per cycle max change
OUTPUT_MIN = 0.0          # mA
OUTPUT_MAX = 7.5          # mA

# Control loop timing
DEFAULT_CYCLE_PERIOD_MS = 10  # ms (100 Hz control rate)
NEURAL_DELAY_CYCLES = 5   # cycles (50 ms neural latency)

# Safety monitor thresholds
MONITOR_STIM_LIMIT = 7.0  # mA (warning threshold)
MONITOR_RATE_LIMIT = 0.15 # mA/cycle (warning threshold)
MONITOR_OSC_ZCR_THRESHOLD = 0.4  # Zero-crossing rate threshold
MONITOR_INTEGRAL_WARN = 30.0    # Integral value warning
MONITOR_ENERGY_MULTIPLIER = 3.0 # x baseline triggers warning
MONITOR_MAX_JITTER_MS = 2.0     # Max allowed cycle time deviation
MONITOR_FEATURE_SHIFT_DB = 8.0  # dB: max allowed mean shift between windows
MONITOR_FEATURE_WINDOW = 20     # cycles for shift detection

# Energy model (uJ per operation)
ENERGY_SENSE_PER_CYCLE = 0.5    # uJ
ENERGY_PROCESS_PER_CYCLE = 2.0  # uJ
ENERGY_CONTROL_PER_CYCLE = 0.1 # uJ
ENERGY_ACTUATE_PER_PULSE = 15.0 # uJ per stimulation pulse
ENERGY_MONITOR_PER_CYCLE = 0.3 # uJ
ENERGY_WIRELESS_TX = 15.0       # uJ per packet
ENERGY_WIRELESS_RX = 2.5       # uJ per packet

BATTERY_CAPACITY_UJ = 1000.0 * 3600 * 3.7 * 1e6  # 1000 mAh at 3.7V in uJ


class SystemState(Enum):
    """Closed-loop system operating states."""
    INIT = auto()
    OPEN_LOOP = auto()
    CLOSED_LOOP = auto()
    SAFE_MODE = auto()
    FAULT = auto()


class MonitorResponse(Enum):
    """Safety monitor response levels."""
    NONE = 0
    LOG_AND_CONTINUE = 1
    INCREASE_MONITORING = 2
    SWITCH_OPEN_LOOP = 3
    REDUCE_STIMULATION = 4
    DISABLE_STIMULATION = 5
    EMERGENCY_SHUTDOWN = 6


class SecurityEventType(Enum):
    """Types of security events logged by the monitor."""
    SENSOR_ANOMALY = "sensor_anomaly"
    OUTPUT_LIMIT = "output_limit"
    RATE_VIOLATION = "rate_violation"
    INSTABILITY = "instability"
    PARAMETER_TAMPER = "parameter_tamper"
    SETPOINT_TAMPER = "setpoint_tamper"
    TIMING_ANOMALY = "timing_anomaly"
    ENERGY_ANOMALY = "energy_anomaly"
    MONITOR_EVASION = "monitor_evasion"
    INTEGRAL_WINDUP = "integral_windup"
    FEEDBACK_LOSS = "feedback_loss"
    NAN_DETECTED = "nan_detected"


# ============================================================================
# Neural Signal Model
# ============================================================================

class NeuralSignalModel:
    """Generates realistic beta-band LFP signals for simulation.

    Combines:
      1. Oscillatory component (sum of beta-band sinusoids with varying amp)
      2. Background pink noise (1/f filtered to beta band)
      3. Sensor white noise (ADC thermal noise)

    The amplitude is modulated by a slow process and by stimulation
    (stimulation suppresses beta with first-order dynamics).
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.t = 0.0
        self.cycle_period = DEFAULT_CYCLE_PERIOD_MS / 1000.0

        # Beta oscillation components (3-5 sinusoids)
        n_components = 4
        self.freqs = [DOMINANT_BETA_FREQ + self.rng.uniform(-3, 3)
                      for _ in range(n_components)]
        self.phases = [self.rng.uniform(0, 2 * math.pi)
                       for _ in range(n_components)]
        self.base_amps = [1.0 / n_components for _ in range(n_components)]

        # Amplitude modulation (slow, 1-10 s timescale)
        self.amp_mod_freq = self.rng.uniform(0.1, 0.3)  # Hz
        self.amp_mod_phase = self.rng.uniform(0, 2 * math.pi)

        # Current beta amplitude (modulated by stimulation)
        self.current_beta_amp = 1.0
        self.stim_effect = 0.0  # Accumulated stimulation suppression

    def generate_samples(self, n_samples: int, sample_rate: int = 1000) -> List[float]:
        """Generate n_samples of neural signal at given sample rate."""
        dt = 1.0 / sample_rate
        samples = []
        for i in range(n_samples):
            t = self.t + i * dt

            # Slow amplitude modulation
            amp_mod = 1.0 + AMPLITUDE_VARIABILITY * math.sin(
                2 * math.pi * self.amp_mod_freq * t + self.amp_mod_phase)

            # Oscillatory component
            osc = 0.0
            for f, phi, a in zip(self.freqs, self.phases, self.base_amps):
                osc += a * self.current_beta_amp * amp_mod * math.sin(
                    2 * math.pi * f * t + phi)

            # Background noise (simulated pink noise via filtered random)
            pink = self.rng.gauss(0, 0.2)

            # Sensor white noise
            white = self.rng.gauss(0, SIGNAL_NOISE_STD * 0.1)

            samples.append(osc + pink + white)

        self.t += n_samples * dt
        return samples

    def update_stim_effect(self, stim_amplitude: float):
        """Update neural response to stimulation (first-order dynamics).

        beta_amp[n+1] = alpha * beta_amp[n] + (1-alpha) * target
        where target = 1 / (1 + K * stim)
        """
        alpha = math.exp(-self.cycle_period / PLANT_TAU)
        target = 1.0 / (1.0 + STIM_COUPLING_K * stim_amplitude)
        self.current_beta_amp = alpha * self.current_beta_amp + (1 - alpha) * target

    def get_beta_power_db(self) -> float:
        """Get current beta power in dB relative to baseline."""
        power_linear = self.current_beta_amp ** 2
        if power_linear < 1e-10:
            return -60.0
        return 10.0 * math.log10(power_linear)


class FeatureExtractor:
    """Simulates the DSP pipeline: bandpass filter + bandpower estimation.

    In a real system this would use scipy/numpy FFT. Here we approximate
    by computing RMS power of the generated signal (which is already
    band-limited by construction).
    """

    def __init__(self, window_size: int = 20):
        self.window_size = window_size

    def extract(self, samples: List[float]) -> float:
        """Extract beta-band power in dB from raw samples.

        Returns power in dB relative to baseline (where baseline RMS = 1.0).
        """
        if len(samples) < self.window_size:
            samples = samples + [0.0] * (self.window_size - len(samples))
        window = samples[:self.window_size]
        rms = math.sqrt(sum(s**2 for s in window) / len(window))
        if rms < 1e-10:
            return -60.0
        return 10.0 * math.log10(rms ** 2)


# ============================================================================
# PI Controller
# ============================================================================

class PIController:
    """Proportional-Integral controller with anti-windup and rate limiting.

    Discrete implementation:
      u[n] = u[n-1] + (Kp + Ki*T)*e[n] - Kp*e[n-1]
    With clamping anti-windup and output rate limiting.
    """

    def __init__(self, kp: float = DEFAULT_KP, ki: float = DEFAULT_KI,
                 setpoint: float = DEFAULT_SETPOINT,
                 output_min: float = OUTPUT_MIN,
                 output_max: float = OUTPUT_MAX,
                 rate_limit: float = RATE_LIMIT,
                 integral_limit: float = INTEGRAL_LIMIT,
                 cycle_period: float = DEFAULT_CYCLE_PERIOD_MS / 1000.0,
                 enable_anti_windup: bool = True,
                 enable_rate_limit: bool = True):
        self.kp = kp
        self.ki = ki
        self.setpoint = setpoint
        self.output_min = output_min
        self.output_max = output_max
        self.rate_limit = rate_limit
        self.integral_limit = integral_limit
        self.cycle_period = cycle_period
        self.enable_anti_windup = enable_anti_windup
        self.enable_rate_limit = enable_rate_limit

        # State
        self.integral = 0.0
        self.prev_error = 0.0
        self.output = 0.0
        self.prev_output = 0.0
        self.saturated = False

        # Authorized values (for tamper detection)
        self._auth_kp = kp
        self._auth_ki = ki
        self._auth_setpoint = setpoint

    def compute(self, measured_value: float) -> float:
        """Compute one control step.

        Args:
            measured_value: Current beta power in dB
        Returns:
            Stimulation amplitude in mA
        """
        # Error computation
        error = self.setpoint - measured_value

        # Proportional term
        p_term = self.kp * error

        # Integral update with anti-windup
        if self.enable_anti_windup and (self.saturated):
            pass  # Don't accumulate when saturated
        else:
            self.integral += self.ki * error * self.cycle_period

        # Clamp integral
        if abs(self.integral) > self.integral_limit:
            self.integral = math.copysign(self.integral_limit, self.integral)

        i_term = self.integral

        # Total output
        raw_output = p_term + i_term

        # Rate limiting
        if self.enable_rate_limit:
            delta = raw_output - self.prev_output
            if abs(delta) > self.rate_limit:
                raw_output = self.prev_output + math.copysign(self.rate_limit, delta)

        # Output clamping
        clamped = False
        if raw_output > self.output_max:
            raw_output = self.output_max
            clamped = True
        elif raw_output < self.output_min:
            raw_output = self.output_min
            clamped = True

        self.saturated = clamped
        self.output = raw_output
        self.prev_output = raw_output
        self.prev_error = error

        return raw_output

    def is_parameter_authentic(self) -> bool:
        """Check if current parameters match authorized values."""
        return (abs(self.kp - self._auth_kp) < 1e-9 and
                abs(self.ki - self._auth_ki) < 1e-9 and
                abs(self.setpoint - self._auth_setpoint) < 1e-9)

    def reset(self):
        """Reset controller state (used after safe mode recovery)."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.output = 0.0
        self.prev_output = 0.0
        self.saturated = False


# ============================================================================
# Stimulation Actuator
# ============================================================================

class StimulationActuator:
    """Simulates the stimulation output stage with charge balance."""

    def __init__(self, enable_charge_balance: bool = True):
        self.enable_charge_balance = charge_balance_ok = enable_charge_balance
        self.stim_freq = 130.0  # Hz (typical DBS)
        self.pulse_width_us = 60.0  # us
        self.current_amplitude = 0.0  # mA
        self.charge_balance_ok = True
        self.total_pulses = 0
        self.total_charge_uC = 0.0

    def deliver(self, amplitude_ma: float) -> Dict:
        """Deliver one cycle's worth of stimulation.

        Returns dict with delivery details.
        """
        self.current_amplitude = max(0.0, min(amplitude_ma, OUTPUT_MAX))

        # Number of pulses in one control cycle
        n_pulses = int(self.stim_freq * DEFAULT_CYCLE_PERIOD_MS / 1000.0)
        n_pulses = max(0, n_pulses)

        # Charge per pulse (uA * us = pC, convert to uC)
        charge_per_phase = self.current_amplitude * 1000 * self.pulse_width_us / 1e6  # uC
        total_charge = charge_per_phase * n_pulses * 2  # cathodic + anodic

        # Charge balance check
        self.charge_balance_ok = True
        if not self.enable_charge_balance:
            self.charge_balance_ok = False

        self.total_pulses += n_pulses
        self.total_charge_uC += total_charge

        return {
            "amplitude_ma": self.current_amplitude,
            "frequency_hz": self.stim_freq,
            "pulse_width_us": self.pulse_width_us,
            "n_pulses": n_pulses,
            "charge_per_cycle_uC": round(total_charge, 4),
            "charge_balance_ok": self.charge_balance_ok
        }


# ============================================================================
# Energy Model
# ============================================================================

class EnergyModel:
    """Tracks energy consumption for battery depletion analysis."""

    def __init__(self, battery_capacity_uj: float = BATTERY_CAPACITY_UJ):
        self.battery_capacity = battery_capacity_uj
        self.energy_used = 0.0
        self.cycle_count = 0
        self.stim_energy = 0.0
        self.sense_energy = 0.0
        self.process_energy = 0.0
        self.control_energy = 0.0
        self.monitor_energy = 0.0
        self.wireless_energy = 0.0
        self.wireless_packets = 0

    def record_cycle(self, n_stim_pulses: int = 0, wireless_packets: int = 0):
        """Record energy for one control cycle."""
        self.cycle_count += 1
        e_sense = ENERGY_SENSE_PER_CYCLE
        e_process = ENERGY_PROCESS_PER_CYCLE
        e_control = ENERGY_CONTROL_PER_CYCLE
        e_monitor = ENERGY_MONITOR_PER_CYCLE
        e_stim = n_stim_pulses * ENERGY_ACTUATE_PER_PULSE
        e_wireless = wireless_packets * (ENERGY_WIRELESS_TX + ENERGY_WIRELESS_RX)

        self.sense_energy += e_sense
        self.process_energy += e_process
        self.control_energy += e_control
        self.monitor_energy += e_monitor
        self.stim_energy += e_stim
        self.wireless_energy += e_wireless
        self.wireless_packets += wireless_packets
        self.energy_used += (e_sense + e_process + e_control +
                              e_monitor + e_stim + e_wireless)

    def get_power_uw(self) -> float:
        """Average power in microwatts."""
        if self.cycle_count == 0:
            return 0.0
        cycle_time_s = DEFAULT_CYCLE_PERIOD_MS / 1000.0
        return self.energy_used / (self.cycle_count * cycle_time_s)

    def get_battery_percent(self) -> float:
        """Remaining battery percentage."""
        return max(0.0, (1.0 - self.energy_used / self.battery_capacity) * 100.0)

    def get_projected_life_hours(self) -> float:
        """Projected battery life in hours at current consumption rate."""
        power_uw = self.get_power_uw()
        if power_uw < 1e-6:
            return float('inf')
        remaining_uj = self.battery_capacity - self.energy_used
        return remaining_uj / (power_uw * 1e-6) / 3600.0

    def to_dict(self) -> Dict:
        return {
            "battery_percent": round(self.get_battery_percent(), 4),
            "avg_power_uw": round(self.get_power_uw(), 2),
            "projected_life_hours": round(self.get_projected_life_hours(), 1),
            "total_energy_uj": round(self.energy_used, 1),
            "stim_energy_pct": round(
                100 * self.stim_energy / max(1, self.energy_used), 1),
            "wireless_packets": self.wireless_packets
        }


# ============================================================================
# Safety Monitor
# ============================================================================

@dataclass
class MonitorAlert:
    """Record of a safety monitor alert."""
    cycle: int
    event_type: str
    severity: int  # 1-6
    details: Dict = field(default_factory=dict)


def _mr(a: MonitorResponse, b: MonitorResponse) -> MonitorResponse:
    """Max of two MonitorResponse enums by value."""
    return MonitorResponse(max(a.value, b.value))


class SafetyMonitor:
    """Independent safety monitor for the closed-loop system.

    Implements 5 validation points (VP-CL-01 through VP-CL-05 from Section 31):
      VP-CL-01: Feature value range
      VP-CL-02: Output rate of change
      VP-CL-03: Output absolute limits
      VP-CL-04: Parameter integrity (via controller.is_parameter_authentic)
      VP-CL-06: Stability indicator (zero-crossing rate)
    Plus: integral windup, timing, energy, and NaN checks.
    """

    def __init__(self, controller: PIController,
                 feature_min: float = -40.0,
                 feature_max: float = 20.0,
                 enable_parameter_check: bool = True,
                 enable_stability_check: bool = True,
                 enable_energy_check: bool = True,
                 enable_timing_check: bool = True,
                 enable_instability_response: bool = True,
                 vulnerable: bool = False):
        self.controller = controller
        self.feature_min = feature_min
        self.feature_max = feature_max
        self.enable_parameter_check = enable_parameter_check
        self.enable_stability_check = enable_stability_check
        self.enable_energy_check = enable_energy_check
        self.enable_timing_check = enable_timing_check
        self.enable_instability_response = enable_instability_response
        self.vulnerable = vulnerable

        # History for stability analysis
        self.output_history: List[float] = []
        self.feature_history: List[float] = []
        self.alerts: List[MonitorAlert] = []
        self.alert_counts: Dict[str, int] = {}

        # Stability detection state
        self.zcr_window: List[float] = []
        self.zcr_window_size = 50  # cycles

        # Cumulative anomaly tracking for escalation
        self.consecutive_anomalies = 0
        self.escalation_threshold = 10  # cycles of persistent anomaly before escalation

    def check(self, cycle: int, feature: float, output: float,
              integral: float, cycle_time_ms: float,
              energy: EnergyModel) -> Tuple[MonitorResponse, List[MonitorAlert]]:
        """Run all monitor checks for one cycle.

        Returns (response_level, list_of_new_alerts).
        """
        new_alerts = []
        max_response = MonitorResponse.NONE

        # --- VP-CL-01: Feature value range ---
        feature_anomaly = False
        if feature < self.feature_min or feature > self.feature_max:
            feature_anomaly = True
            alert = MonitorAlert(
                cycle=cycle,
                event_type=SecurityEventType.SENSOR_ANOMALY.value,
                severity=2,
                details={"feature": feature,
                         "bounds": [self.feature_min, self.feature_max]})
            new_alerts.append(alert)
            max_response = _mr(max_response, MonitorResponse.LOG_AND_CONTINUE)

        # NaN check
        if math.isnan(feature) or math.isinf(feature):
            alert = MonitorAlert(
                cycle=cycle,
                event_type=SecurityEventType.NAN_DETECTED.value,
                severity=4,
                details={"feature": str(feature)})
            new_alerts.append(alert)
            max_response = MonitorResponse.DISABLE_STIMULATION

        # --- VP-CL-02: Output rate of change ---
        rate_anomaly = False
        if len(self.output_history) > 0:
            rate = abs(output - self.output_history[-1])
            if rate > MONITOR_RATE_LIMIT:
                rate_anomaly = True
                alert = MonitorAlert(
                    cycle=cycle,
                    event_type=SecurityEventType.RATE_VIOLATION.value,
                    severity=2,
                    details={"rate": round(rate, 4),
                             "limit": MONITOR_RATE_LIMIT})
                new_alerts.append(alert)
                max_response = _mr(max_response,
                                  MonitorResponse.LOG_AND_CONTINUE)

        # --- VP-CL-03: Output absolute limits ---
        if output > MONITOR_STIM_LIMIT:
            alert = MonitorAlert(
                cycle=cycle,
                event_type=SecurityEventType.OUTPUT_LIMIT.value,
                severity=3,
                details={"output": round(output, 4),
                         "limit": MONITOR_STIM_LIMIT})
            new_alerts.append(alert)
            max_response = _mr(max_response, MonitorResponse.REDUCE_STIMULATION)

        # --- VP-CL-04: Parameter integrity ---
        if self.enable_parameter_check and not self.vulnerable:
            if not self.controller.is_parameter_authentic():
                alert = MonitorAlert(
                    cycle=cycle,
                    event_type=SecurityEventType.PARAMETER_TAMPER.value,
                    severity=4,
                    details={
                        "current_kp": self.controller.kp,
                        "auth_kp": self.controller._auth_kp,
                        "current_ki": self.controller.ki,
                        "auth_ki": self.controller._auth_ki,
                        "current_setpoint": self.controller.setpoint,
                        "auth_setpoint": self.controller._auth_setpoint
                    })
                new_alerts.append(alert)
                max_response = _mr(max_response, MonitorResponse.SWITCH_OPEN_LOOP)

        # --- Integral windup ---
        if abs(integral) > MONITOR_INTEGRAL_WARN:
            alert = MonitorAlert(
                cycle=cycle,
                event_type=SecurityEventType.INTEGRAL_WINDUP.value,
                severity=2,
                details={"integral": round(integral, 4),
                         "warn_threshold": MONITOR_INTEGRAL_WARN})
            new_alerts.append(alert)
            max_response = _mr(max_response, MonitorResponse.LOG_AND_CONTINUE)

        # --- VP-CL-06: Stability (oscillation detection) ---
        self.output_history.append(output)
        self.feature_history.append(feature)
        if self.enable_stability_check and len(self.output_history) > 100:
            zcr = self._compute_zcr()
            if zcr > MONITOR_OSC_ZCR_THRESHOLD:
                alert = MonitorAlert(
                    cycle=cycle,
                    event_type=SecurityEventType.INSTABILITY.value,
                    severity=4,
                    details={"zcr": round(zcr, 4),
                             "threshold": MONITOR_OSC_ZCR_THRESHOLD})
                new_alerts.append(alert)
                if self.enable_instability_response:
                    max_response = _mr(max_response,
                                      MonitorResponse.SWITCH_OPEN_LOOP)

        # --- Timing anomaly ---
        if self.enable_timing_check:
            timing_dev = abs(cycle_time_ms - DEFAULT_CYCLE_PERIOD_MS)
            if timing_dev > MONITOR_MAX_JITTER_MS:
                alert = MonitorAlert(
                    cycle=cycle,
                    event_type=SecurityEventType.TIMING_ANOMALY.value,
                    severity=2,
                    details={"cycle_time_ms": round(cycle_time_ms, 2),
                             "nominal_ms": DEFAULT_CYCLE_PERIOD_MS,
                             "deviation_ms": round(timing_dev, 2)})
                new_alerts.append(alert)
                max_response = _mr(max_response,
                                  MonitorResponse.LOG_AND_CONTINUE)

        # --- Energy anomaly ---
        if self.enable_energy_check and energy.cycle_count > 100:
            baseline_power = (ENERGY_SENSE_PER_CYCLE + ENERGY_PROCESS_PER_CYCLE +
                              ENERGY_CONTROL_PER_CYCLE + ENERGY_MONITOR_PER_CYCLE +
                              1 * ENERGY_ACTUATE_PER_PULSE)  # ~1 pulse/cycle baseline
            baseline_power /= (DEFAULT_CYCLE_PERIOD_MS / 1000.0)
            current_power = energy.get_power_uw()
            if current_power > baseline_power * MONITOR_ENERGY_MULTIPLIER:
                alert = MonitorAlert(
                    cycle=cycle,
                    event_type=SecurityEventType.ENERGY_ANOMALY.value,
                    severity=2,
                    details={"power_uw": round(current_power, 2),
                             "baseline_uw": round(baseline_power, 2),
                             "multiplier": round(
                                 current_power / max(1, baseline_power), 2)})
                new_alerts.append(alert)
                max_response = _mr(max_response,
                                  MonitorResponse.LOG_AND_CONTINUE)

        # --- VP-CL-07: Feature statistical shift detection ---
        # Maintain a rolling buffer and compare two adjacent windows
        self.feature_history.append(feature)
        buf_len = len(self.feature_history)
        win = MONITOR_FEATURE_WINDOW
        if buf_len >= win * 2:
            mean_a = sum(self.feature_history[-win*2:-win]) / win
            mean_b = sum(self.feature_history[-win:]) / win
            shift = abs(mean_b - mean_a)
            if shift > MONITOR_FEATURE_SHIFT_DB:
                alert = MonitorAlert(
                    cycle=cycle,
                    event_type=SecurityEventType.SENSOR_ANOMALY.value,
                    severity=3,
                    details={"feature_shift_db": round(shift, 2),
                             "window_means": [round(mean_a, 2), round(mean_b, 2)],
                             "threshold": MONITOR_FEATURE_SHIFT_DB})
                new_alerts.append(alert)
                max_response = _mr(max_response, MonitorResponse.INCREASE_MONITORING)

        # --- Cumulative anomaly escalation ---
        # Track consecutive cycles with any anomaly for escalation
        has_anomaly = len(new_alerts) > 0
        if has_anomaly:
            self.consecutive_anomalies += 1
        else:
            self.consecutive_anomalies = 0

        # Escalate to OPEN_LOOP if anomalies persist (secure mode only)
        if not self.vulnerable and self.consecutive_anomalies >= self.escalation_threshold:
            max_response = _mr(max_response, MonitorResponse.SWITCH_OPEN_LOOP)
            if not any(a.event_type == "cumulative_escalation" for a in new_alerts):
                esc_alert = MonitorAlert(
                    cycle=cycle,
                    event_type="cumulative_escalation",
                    severity=3,
                    details={"consecutive_anomalies": self.consecutive_anomalies,
                             "threshold": self.escalation_threshold})
                new_alerts.append(esc_alert)

        self.alerts.extend(new_alerts)
        for a in new_alerts:
            self.alert_counts[a.event_type] = \
                self.alert_counts.get(a.event_type, 0) + 1

        return max_response, new_alerts

    def _compute_zcr(self) -> float:
        """Compute zero-crossing rate of recent output."""
        window = self.output_history[-self.zcr_window_size:]
        if len(window) < 10:
            return 0.0
        mean = sum(window) / len(window)
        crossings = sum(1 for i in range(1, len(window))
                       if (window[i] - mean) * (window[i-1] - mean) < 0)
        return crossings / len(window)

    def to_dict(self) -> Dict:
        return {
            "total_alerts": len(self.alerts),
            "alert_counts": dict(self.alert_counts),
            "last_10_alerts": [
                {"cycle": a.cycle, "type": a.event_type,
                 "severity": a.severity, "details": a.details}
                for a in self.alerts[-10:]
            ]
        }


# ============================================================================
# Closed-Loop System (Main Simulator)
# ============================================================================

class ClosedLoopSystem:
    """Complete closed-loop DBS simulation with security instrumentation.

    Integrates: NeuralSignalModel -> FeatureExtractor -> PIController ->
                StimulationActuator -> (neural response) -> loop back.
    Plus: SafetyMonitor, EnergyModel, security event logging.
    """

    def __init__(self, seed: int = 42, vulnerable: bool = False,
                 num_cycles: int = 1000):
        self.rng = random.Random(seed + 1)
        self.vulnerable = vulnerable
        self.num_cycles = num_cycles
        self.cycle_period_s = DEFAULT_CYCLE_PERIOD_MS / 1000.0

        # System state
        self.state = SystemState.INIT
        self.cycle = 0

        # Sub-systems
        self.neural_model = NeuralSignalModel(seed=seed)
        self.feature_extractor = FeatureExtractor(window_size=20)
        self.controller = PIController()
        self.actuator = StimulationActuator(
            enable_charge_balance=not vulnerable)
        self.energy = EnergyModel()
        self.monitor = SafetyMonitor(
            controller=self.controller, vulnerable=vulnerable)

        # Vulnerable mode: disable key security features
        if vulnerable:
            self.monitor.enable_parameter_check = False
            self.monitor.enable_stability_check = False
            self.monitor.enable_timing_check = False
            self.controller.enable_anti_windup = False
            self.controller.enable_rate_limit = False

        # Logging
        self.cycle_log: List[Dict] = []
        self.security_events: List[Dict] = []

        # Attack injection interface (used by Lab 002)
        self.attack_active = False
        self.attack_type = None
        self.attack_start_cycle = -1
        self.attack_end_cycle = -1
        self.attack_params: Dict = {}
        self.sensor_offset_db = 0.0
        self.delay_cycles = 0
        self.delay_buffer: List[float] = []

    def set_attack(self, attack_type: str, start_cycle: int,
                   end_cycle: int, **params):
        """Configure an attack injection for simulation.

        Attack types:
          sensor_spoof  — inject offset into sensed beta power (params: offset_db, gradual)
          gain_modify  — change controller gains (params: kp_mult, ki_mult)
          setpoint_modify — change setpoint (params: setpoint_db)
          delay_inject — add delay cycles (params: delay_cycles)
          feedback_bypass — force open-loop (params: none)
          energy_flood — force max stimulation (params: none)
          monitor_evasion — disable monitor checks (params: none)
        """
        self.attack_active = True
        self.attack_type = attack_type
        self.attack_start_cycle = start_cycle
        self.attack_end_cycle = end_cycle
        self.attack_params = params

    def _apply_attack(self):
        """Apply attack effects for the current cycle."""
        if not self.attack_active:
            return
        if self.cycle < self.attack_start_cycle or self.cycle > self.attack_end_cycle:
            return

        atype = self.attack_type
        progress = (self.cycle - self.attack_start_cycle) / max(
            1, self.attack_end_cycle - self.attack_start_cycle)

        if atype == "sensor_spoof":
            offset = self.attack_params.get("offset_db", 10.0)
            gradual = self.attack_params.get("gradual", False)
            if gradual:
                self.sensor_offset_db = offset * min(1.0, progress * 3)
            else:
                self.sensor_offset_db = offset

        elif atype == "gain_modify":
            kp_mult = self.attack_params.get("kp_mult", 5.0)
            ki_mult = self.attack_params.get("ki_mult", 5.0)
            gradual = self.attack_params.get("gradual", False)
            if gradual:
                factor = min(1.0, progress * 2)
                self.controller.kp = self.controller._auth_kp * (1 + (kp_mult - 1) * factor)
                self.controller.ki = self.controller._auth_ki * (1 + (ki_mult - 1) * factor)
            else:
                self.controller.kp = self.controller._auth_kp * kp_mult
                self.controller.ki = self.controller._auth_ki * ki_mult

        elif atype == "setpoint_modify":
            new_sp = self.attack_params.get("setpoint_db", 10.0)
            gradual = self.attack_params.get("gradual", False)
            if gradual:
                self.controller.setpoint = self.controller._auth_setpoint + \
                    (new_sp - self.controller._auth_setpoint) * min(1.0, progress * 3)
            else:
                self.controller.setpoint = new_sp

        elif atype == "delay_inject":
            self.delay_cycles = self.attack_params.get("delay_cycles", 5)

        elif atype == "feedback_bypass":
            self.state = SystemState.OPEN_LOOP

        elif atype == "energy_flood":
            self.sensor_offset_db = -15.0  # Make controller think beta is very low
            # This causes max stimulation to "raise" beta

        elif atype == "monitor_evasion":
            self.monitor.enable_parameter_check = False
            self.monitor.enable_stability_check = False
            self.monitor.enable_timing_check = False

    def _remove_attack(self):
        """Remove attack effects (when attack period ends)."""
        self.sensor_offset_db = 0.0
        self.delay_cycles = 0
        self.delay_buffer.clear()
        if self.attack_type in ("gain_modify",):
            self.controller.kp = self.controller._auth_kp
            self.controller.ki = self.controller._auth_ki
        if self.attack_type in ("setpoint_modify",):
            self.controller.setpoint = self.controller._auth_setpoint
        if self.attack_type == "monitor_evasion" and not self.vulnerable:
            self.monitor.enable_parameter_check = True
            self.monitor.enable_stability_check = True
            self.monitor.enable_timing_check = True

    def run(self) -> Dict:
        """Run the complete closed-loop simulation.

        Returns a dict with full simulation results.
        """
        start_time = time.time()

        # INIT phase (10 cycles)
        for _ in range(10):
            self.neural_model.generate_samples(10)
            self.energy.record_cycle()
            self.cycle += 1

        self.state = SystemState.CLOSED_LOOP

        # Main control loop
        for c in range(self.num_cycles):
            cycle_start = time.time()

            # Check if attack should start/end
            if self.attack_active:
                if self.cycle == self.attack_start_cycle:
                    self._apply_attack()
                if self.cycle == self.attack_end_cycle + 1:
                    self._remove_attack()
                # Re-apply each cycle for gradual attacks
                if (self.attack_start_cycle <= self.cycle <=
                        self.attack_end_cycle):
                    self._apply_attack()

            # 1. SENSE: Generate neural samples
            samples = self.neural_model.generate_samples(10, 1000)

            # 2. PROCESS: Extract beta power feature
            raw_beta = self.feature_extractor.extract(samples)

            # Apply sensor spoofing offset
            sensed_beta = raw_beta + self.sensor_offset_db

            # Apply delay injection
            if self.delay_cycles > 0:
                self.delay_buffer.append(sensed_beta)
                if len(self.delay_buffer) > self.delay_cycles:
                    sensed_beta = self.delay_buffer.pop(0)
                else:
                    sensed_beta = raw_beta  # Use un-delayed during fill

            # 3. CONTROL: Compute stimulation adjustment
            if self.state == SystemState.CLOSED_LOOP:
                stim_output = self.controller.compute(sensed_beta)
            else:
                # Open loop / safe mode: hold last output or use default
                stim_output = max(1.0, self.controller.output * 0.5)

            # 4. ACTUATE: Deliver stimulation
            stim_info = self.actuator.deliver(stim_output)

            # 5. UPDATE NEURAL MODEL: Stimulation suppresses beta
            self.neural_model.update_stim_effect(stim_output)

            # 6. MONITOR: Safety checks
            cycle_time = (time.time() - cycle_start) * 1000  # ms
            # Use nominal timing for simulation (real time is unreliable)
            cycle_time = DEFAULT_CYCLE_PERIOD_MS + self.rng.gauss(0, 0.1)

            response, alerts = self.monitor.check(
                cycle=self.cycle,
                feature=sensed_beta,
                output=stim_output,
                integral=self.controller.integral,
                cycle_time_ms=cycle_time,
                energy=self.energy
            )

            # Handle monitor response
            if response.value >= MonitorResponse.SWITCH_OPEN_LOOP.value:
                if self.state == SystemState.CLOSED_LOOP:
                    self.state = SystemState.SAFE_MODE
                    self.security_events.append({
                        "cycle": self.cycle,
                        "event": "monitor_triggered",
                        "response": response.name,
                        "primary_alert": alerts[0].event_type if alerts else "unknown"
                    })
            elif response.value >= MonitorResponse.REDUCE_STIMULATION.value:
                # Reduce stimulation by 50%
                stim_output *= 0.5
                self.actuator.deliver(stim_output)

            if response.value >= MonitorResponse.DISABLE_STIMULATION.value:
                self.state = SystemState.SAFE_MODE
                stim_output = 0.0

            # 7. ENERGY: Record consumption
            wireless_pkts = 1 if self.cycle % 100 == 0 else 0  # Telemetry every 100 cycles
            self.energy.record_cycle(
                n_stim_pulses=stim_info["n_pulses"],
                wireless_packets=wireless_pkts
            )

            # 8. LOG: Record cycle data
            cycle_data = {
                "cycle": self.cycle,
                "state": self.state.name,
                "raw_beta_db": round(raw_beta, 3),
                "sensed_beta_db": round(sensed_beta, 3),
                "sensor_offset_db": round(self.sensor_offset_db, 3),
                "stim_output_ma": round(stim_output, 4),
                "controller_integral": round(self.controller.integral, 4),
                "controller_error": round(self.controller.prev_error, 3),
                "beta_amplitude": round(self.neural_model.current_beta_amp, 4),
                "charge_balance_ok": self.actuator.charge_balance_ok,
                "battery_pct": round(self.energy.get_battery_percent(), 4),
                "monitor_response": response.name,
                "n_alerts": len(alerts)
            }
            self.cycle_log.append(cycle_data)

            # Log security events
            for a in alerts:
                self.security_events.append({
                    "cycle": self.cycle,
                    "event": a.event_type,
                    "severity": a.severity,
                    "details": a.details
                })

            self.cycle += 1

        elapsed = time.time() - start_time

        return self._compile_results(elapsed)

    def _compile_results(self, elapsed_s: float) -> Dict:
        """Compile simulation results into output dict."""
        stim_outputs = [c["stim_output_ma"] for c in self.cycle_log]
        sensed_betas = [c["sensed_beta_db"] for c in self.cycle_log]
        raw_betas = [c["raw_beta_db"] for c in self.cycle_log]

        return {
            "simulation": {
                "vulnerable": self.vulnerable,
                "num_cycles": self.num_cycles,
                "cycle_period_ms": DEFAULT_CYCLE_PERIOD_MS,
                "elapsed_s": round(elapsed_s, 3),
                "attack": {
                    "active": self.attack_active,
                    "type": self.attack_type,
                    "start": self.attack_start_cycle,
                    "end": self.attack_end_cycle,
                    "params": self.attack_params
                } if self.attack_active else None
            },
            "controller": {
                "kp": self.controller.kp,
                "ki": self.controller.ki,
                "setpoint": self.controller.setpoint,
                "auth_kp": self.controller._auth_kp,
                "auth_ki": self.controller._auth_ki,
                "auth_setpoint": self.controller._auth_setpoint,
                "parameter_authentic": self.controller.is_parameter_authentic()
            },
            "statistics": {
                "stim_mean_ma": round(
                    sum(stim_outputs) / max(1, len(stim_outputs)), 4),
                "stim_max_ma": round(max(stim_outputs), 4) if stim_outputs else 0,
                "stim_min_ma": round(min(stim_outputs), 4) if stim_outputs else 0,
                "beta_mean_db": round(
                    sum(sensed_betas) / max(1, len(sensed_betas)), 3),
                "beta_range_db": [
                    round(min(sensed_betas), 3) if sensed_betas else 0,
                    round(max(sensed_betas), 3) if sensed_betas else 0
                ],
                "final_beta_amplitude": round(
                    self.neural_model.current_beta_amp, 4)
            },
            "energy": self.energy.to_dict(),
            "monitor": self.monitor.to_dict(),
            "final_state": self.state.name,
            "security_events": self.security_events[:50],
            "cycle_log_sample": self.cycle_log[::max(
                1, len(self.cycle_log) // 50)][:50]
        }


# ============================================================================
# CLI
# ============================================================================

def print_demo_output(results: Dict):
    """Print formatted demo output to console."""
    sim = results["simulation"]
    ctrl = results["controller"]
    stats = results["statistics"]
    energy = results["energy"]
    monitor = results["monitor"]

    print("=" * 70)
    print("  VIREON NL-005 Lab 001: Closed-Loop DBS Simulator (DEMO)")
    print("=" * 70)
    print(f"  Mode:           {'VULNERABLE' if sim['vulnerable'] else 'SECURE'}")
    print(f"  Cycles:         {sim['num_cycles']}")
    print(f"  Cycle period:   {sim['cycle_period_ms']} ms")
    print(f"  Elapsed:        {sim['elapsed_s']} s")
    if sim["attack"] and sim["attack"]["active"]:
        atk = sim["attack"]
        print(f"  Attack:         {atk['type']} (cycles {atk['start']}-{atk['end']})")
    print()
    print(f"  Controller Kp:  {ctrl['kp']}  (auth: {ctrl['auth_kp']})")
    print(f"  Controller Ki:  {ctrl['ki']}  (auth: {ctrl['auth_ki']})")
    print(f"  Setpoint:       {ctrl['setpoint']} dB (auth: {ctrl['auth_setpoint']} dB)")
    print(f"  Params OK:      {ctrl['parameter_authentic']}")
    print()
    print(f"  Stim mean:      {stats['stim_mean_ma']} mA")
    print(f"  Stim range:     [{stats['stim_min_ma']}, {stats['stim_max_ma']}] mA")
    print(f"  Beta mean:      {stats['beta_mean_db']} dB")
    print(f"  Beta range:     {stats['beta_range_db']} dB")
    print(f"  Final beta amp: {stats['final_beta_amplitude']}")
    print()
    print(f"  Battery:        {energy['battery_percent']}%")
    print(f"  Avg power:      {energy['avg_power_uw']} uW")
    print(f"  Projected life: {energy['projected_life_hours']} hours")
    print()
    print(f"  Monitor alerts: {monitor['total_alerts']}")
    if monitor["alert_counts"]:
        for etype, count in sorted(monitor["alert_counts"].items()):
            print(f"    {etype}: {count}")
    print(f"  Security events: {len(results['security_events'])}")
    print("=" * 70)

    # Print sample of cycle log
    print("\n  Cycle log sample (every 10th cycle):")
    print(f"  {'Cycle':>6} {'State':>12} {'RawBeta':>9} {'SensedBeta':>11} "
          f"{'Stim(mA)':>9} {'Integral':>9} {'Monitor':>12}")
    print("  " + "-" * 76)
    log = results.get("cycle_log_sample", [])
    for entry in log:
        print(f"  {entry['cycle']:>6} {entry['state']:>12} "
              f"{entry['raw_beta_db']:>9.2f} {entry['sensed_beta_db']:>11.2f} "
              f"{entry['stim_output_ma']:>9.4f} {entry['controller_integral']:>9.4f} "
              f"{entry['monitor_response']:>12}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="VIREON NL-005 Lab 001: Closed-Loop DBS Simulator")
    parser.add_argument("--mode", choices=["demo", "normal", "attack_test"],
                        default="demo",
                        help="Simulation mode")
    parser.add_argument("--num_cycles", type=int, default=1000,
                        help="Number of control cycles")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")
    parser.add_argument("--output_dir", type=str, default="output",
                        help="Output directory for JSON results")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    if args.mode == "demo":
        print("\n>>> Running SECURE mode demo (200 cycles)...")
        sys_sec = ClosedLoopSystem(seed=args.seed, vulnerable=False,
                                    num_cycles=200)
        results_sec = sys_sec.run()
        print_demo_output(results_sec)

        print("\n>>> Running VULNERABLE mode demo (200 cycles)...")
        sys_vuln = ClosedLoopSystem(seed=args.seed, vulnerable=True,
                                     num_cycles=200)
        results_vuln = sys_vuln.run()
        print_demo_output(results_vuln)

        # Save combined output
        combined = {
            "secure_demo": results_sec,
            "vulnerable_demo": results_vuln
        }
        out_path = os.path.join(output_dir, "demo_output.json")
        with open(out_path, "w") as f:
            json.dump(combined, f, indent=2)
        print(f"\n  Results saved to: {out_path}")

    elif args.mode == "normal":
        print(f"\n>>> Running NORMAL mode ({args.num_cycles} cycles)...")
        sys_cl = ClosedLoopSystem(seed=args.seed, vulnerable=False,
                                    num_cycles=args.num_cycles)
        results = sys_cl.run()
        out_path = os.path.join(output_dir, "closed_loop_session.json")
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"  Results saved to: {out_path}")
        print(f"  Cycles: {results['simulation']['num_cycles']}")
        print(f"  Stim mean: {results['statistics']['stim_mean_ma']} mA")
        print(f"  Monitor alerts: {results['monitor']['total_alerts']}")

    elif args.mode == "attack_test":
        print(f"\n>>> Running ATTACK_TEST mode ({args.num_cycles} cycles)...")
        print("  This mode disables security features to produce vulnerable sessions.")
        sys_cl = ClosedLoopSystem(seed=args.seed, vulnerable=True,
                                    num_cycles=args.num_cycles)
        results = sys_cl.run()
        out_path = os.path.join(output_dir, "vulnerable_session.json")
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"  Results saved to: {out_path}")
        print(f"  Cycles: {results['simulation']['num_cycles']}")
        print(f"  Stim mean: {results['statistics']['stim_mean_ma']} mA")
        print(f"  Monitor alerts: {results['monitor']['total_alerts']}")

    print()


if __name__ == "__main__":
    main()
