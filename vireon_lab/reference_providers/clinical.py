# Copyright 2026 VIREON Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
from typing import List, Tuple, Optional
import math
import threading

from vireon.core.event_bus import EventBus, Event
from vireon.core.safety_envelope import SafetyEnvelope
from vireon.core.utils import calculate_rms
from vireon.core.detection import SecurityEngine
from vireon.core.twin import DigitalTwin

class NeuroIPSConstants:
    SAFE_FALLBACK_AMPLITUDE_MA = 1.0
    SAFE_FALLBACK_FREQUENCY_HZ = 130.0
    STIM_HISTORY_WINDOW_SEC = 10.0
    THERMAL_TAU_DISSIPATION_SEC = 60.0
    MAX_TISSUE_TEMP_CELSIUS = 40.5
    MAX_AMPLITUDE_DELTA = 0.5
    MIN_BETA_POWER = 15.0
    ANOMALY_ACTIVE_WINDOW_SEC = 3.0

class BLEConstants:
    MIN_MTU_SIZE = 23
    MAX_MTU_SIZE = 512
    JAMMING_DROP_RATE_THRESHOLD = 0.3

class NeuroIPS:
    """
    Intrusion Prevention System for Brain-Computer Interfaces.
    Executes automated mitigation actions: clamps stimulation parameters to safe thresholds,
    filters corrupted signals, and enforces link layer security.
    """

    def __init__(self, twin: DigitalTwin, ids: SecurityEngine, event_bus: Optional[EventBus] = None,
                 max_stimulation_amplitude_ma: float = 4.0,
                 max_cumulative_charge: float = 5200.0):
        self.twin = twin
        self.ids = ids
        self.event_bus = event_bus
        self.max_stimulation_amplitude_ma = max_stimulation_amplitude_ma
        self.max_cumulative_charge = max_cumulative_charge

        self.blocked_attacks_count = 0
        self.clamping_active = False
        self.stim_history: List[Tuple[float, float, float]] = []
        self.accumulated_thermal_dose = 0.0
        self.safety_envelope = SafetyEnvelope(max_amplitude_ma=max_stimulation_amplitude_ma)
        self._lock = threading.RLock()

    def sanitize_stimulation_write(self, amplitude: float, frequency: float) -> Tuple[float, float]:
        with self._lock:
            return self._sanitize_stimulation_write(amplitude, frequency)

    def _sanitize_stimulation_write(self, amplitude: float, frequency: float) -> Tuple[float, float]:
        """
        Sanitizes raw stimulator write commands to protect patient tissue.
        Prevents dangerous high-current command injections and cumulative charge buildup.
        """
        if math.isnan(amplitude) or math.isinf(amplitude):
            amplitude = 0.0
        if math.isnan(frequency) or math.isinf(frequency):
            frequency = 0.0
            
        current_time = self.twin.get_sim_clock()
        
        # 1. Safety Envelope Check
        is_safe, new_amp, new_freq = self._check_safety_envelope(amplitude, frequency)
        if not is_safe:
            return new_amp, new_freq

        # 2. Command Rate Limit Check
        is_safe, new_amp, new_freq = self._check_command_rate_limit(amplitude, frequency)
        if not is_safe:
            return new_amp, new_freq

        # 3. Thermal Dose (Leaky Integrator)
        is_safe, new_amp, new_freq = self._update_leaky_integrator(amplitude, frequency, current_time)
        if not is_safe:
            return new_amp, new_freq

        # 4. Thermodynamic protection
        is_safe, new_amp, new_freq = self._check_thermodynamic_limit(amplitude, frequency)
        if not is_safe:
            return new_amp, new_freq

        # 5. Patient State Coherence
        coherence_clamped, amplitude, frequency = self._check_patient_coherence(amplitude, frequency, current_time)
        if coherence_clamped:
            return amplitude, frequency

        # 6. Hard Limit Ceiling
        return self._check_hard_limit(amplitude, frequency, current_time)

    def _check_safety_envelope(self, amplitude: float, frequency: float) -> Tuple[bool, float, float]:
        is_safe, envelope_metrics = self.safety_envelope.evaluate(self.twin)
        if not is_safe:
            self.blocked_attacks_count += 1
            self.clamping_active = True
            self.twin.set_clinical_alert(True, f"IPS Block: Safety Envelope Breach ({envelope_metrics['hazard_state']})")
            self.twin.update_clinical_risk(
                hazard_state=envelope_metrics['hazard_state'],
                iso_severity=envelope_metrics['iso_severity'],
                tissue_damage_risk=envelope_metrics['tissue_damage_risk'],
                clinical_action=envelope_metrics['clinical_action']
            )
            if envelope_metrics['clinical_action'] == "FALLBACK_SAFE_MODE":
                return False, min(amplitude, NeuroIPSConstants.SAFE_FALLBACK_AMPLITUDE_MA), min(frequency, NeuroIPSConstants.SAFE_FALLBACK_FREQUENCY_HZ)
            return False, NeuroIPSConstants.SAFE_FALLBACK_AMPLITUDE_MA, NeuroIPSConstants.SAFE_FALLBACK_FREQUENCY_HZ
        return True, amplitude, frequency

    def _check_command_rate_limit(self, amplitude: float, frequency: float) -> Tuple[bool, float, float]:
        cmd_anomalies = self.ids.analyze_commands(amplitude, frequency)
        if "HIGH_FREQUENCY_COMMAND_ANOMALY" in cmd_anomalies:
            self.blocked_attacks_count += 1
            self.clamping_active = True
            self.twin.set_clinical_alert(True, "IPS Block: Command Jitter Detected")
            self.twin.update_clinical_risk(
                hazard_state="PROTOCOL_ABUSE",
                iso_severity="MARGINAL",
                tissue_damage_risk="NONE",
                clinical_action="RATE_LIMIT"
            )
            if len(self.stim_history) > 0:
                return False, self.stim_history[-1][1], self.stim_history[-1][2]
            return False, NeuroIPSConstants.SAFE_FALLBACK_AMPLITUDE_MA, NeuroIPSConstants.SAFE_FALLBACK_FREQUENCY_HZ
        return True, amplitude, frequency

    def _update_leaky_integrator(self, amplitude: float, frequency: float, current_time: float) -> Tuple[bool, float, float]:
        dt = 0.0
        power_injected = 0.0
        if len(self.stim_history) > 0:
            dt = current_time - self.stim_history[-1][0]
            last_amp = self.stim_history[-1][1]
            last_freq = self.stim_history[-1][2]
            power_injected = abs(last_amp) * abs(last_freq)

        self.stim_history.append((current_time, amplitude, frequency))
        self.stim_history = [x for x in self.stim_history if current_time - x[0] <= NeuroIPSConstants.STIM_HISTORY_WINDOW_SEC]

        if dt > 0:
            tau_dissipation = NeuroIPSConstants.THERMAL_TAU_DISSIPATION_SEC
            decay_factor = np.exp(-dt / tau_dissipation)
            self.accumulated_thermal_dose = (self.accumulated_thermal_dose * decay_factor) + (power_injected * dt)

        if self.accumulated_thermal_dose > self.max_cumulative_charge:
            self.blocked_attacks_count += 1
            self.clamping_active = True
            self.twin.set_clinical_alert(True, "IPS: Cumulative Charge Threat Detected")
            self.twin.update_clinical_risk(
                hazard_state="TISSUE_HEATING",
                iso_severity="CRITICAL",
                tissue_damage_risk="HIGH",
                clinical_action="SHUTDOWN"
            )
            if self.event_bus:
                self.event_bus.publish(Event(
                    topic="ips.cumulative_charge_clamped",
                    data={
                        "accumulated_thermal_dose": self.accumulated_thermal_dose,
                        "limit": self.max_cumulative_charge,
                        "sim_clock": current_time
                    },
                    source="ips"
                ))
            return False, NeuroIPSConstants.SAFE_FALLBACK_AMPLITUDE_MA, NeuroIPSConstants.SAFE_FALLBACK_FREQUENCY_HZ
        return True, amplitude, frequency

    def _check_thermodynamic_limit(self, amplitude: float, frequency: float) -> Tuple[bool, float, float]:
        if self.twin.temperature_celsius >= NeuroIPSConstants.MAX_TISSUE_TEMP_CELSIUS:
            self.blocked_attacks_count += 1
            self.clamping_active = True
            self.twin.set_clinical_alert(True, "IPS: Thermal Tissue Hazard Detected")
            self.twin.update_clinical_risk(
                hazard_state="TISSUE_HEATING",
                iso_severity="CRITICAL",
                tissue_damage_risk="HIGH",
                clinical_action="SHUTDOWN"
            )
            return False, NeuroIPSConstants.SAFE_FALLBACK_AMPLITUDE_MA, NeuroIPSConstants.SAFE_FALLBACK_FREQUENCY_HZ
        return True, amplitude, frequency

    def _check_patient_coherence(self, amplitude: float, frequency: float, current_time: float) -> Tuple[bool, float, float]:
        coherence_clamped = False
        if len(self.stim_history) > 1:
            last_amp = self.stim_history[-2][1]
            
            if abs(amplitude - last_amp) > NeuroIPSConstants.MAX_AMPLITUDE_DELTA:
                amplitude = last_amp + np.sign(amplitude - last_amp) * NeuroIPSConstants.MAX_AMPLITUDE_DELTA
                self.clamping_active = True
                coherence_clamped = True
                self.blocked_attacks_count += 1
                self.twin.set_clinical_alert(True, "IPS Clamped: Coherence Delta Rate Limit")
                self.stim_history[-1] = (current_time, amplitude, frequency)
                
            if len(self.ids.history_beta_power) > 0:
                last_beta = self.ids.history_beta_power[-1]
                active_anomalies = self.ids.detections[-5:]
                has_active_anomaly = any(d["timestamp"] >= current_time - NeuroIPSConstants.ANOMALY_ACTIVE_WINDOW_SEC for d in active_anomalies)
                
                if (last_beta < NeuroIPSConstants.MIN_BETA_POWER or has_active_anomaly) and amplitude > last_amp:
                    amplitude = last_amp
                    self.clamping_active = True
                    coherence_clamped = True
                    self.blocked_attacks_count += 1
                    msg = "IPS Clamped: Coherence State Untrusted (Anomaly Active)" if has_active_anomaly else "IPS Clamped: Coherence State Check Failed"
                    self.twin.set_clinical_alert(True, msg)
                    self.stim_history[-1] = (current_time, amplitude, frequency)

        return coherence_clamped, amplitude, frequency

    def _check_hard_limit(self, amplitude: float, frequency: float, current_time: float) -> Tuple[float, float]:
        if amplitude > self.max_stimulation_amplitude_ma:
            self.blocked_attacks_count += 1
            self.clamping_active = True
            self.twin.set_clinical_alert(True, "IPS Command Clamping Warning")
            self.twin.update_clinical_risk(
                hazard_state="WARNING",
                iso_severity="MARGINAL",
                tissue_damage_risk="NONE",
                clinical_action="MONITOR"
            )
            if self.event_bus:
                self.event_bus.publish(Event(
                    topic="ips.stimulation_clamped",
                    data={
                        "requested_amplitude": amplitude,
                        "clamped_amplitude": self.max_stimulation_amplitude_ma,
                        "sim_clock": current_time
                    },
                    source="ips"
                ))
            return self.max_stimulation_amplitude_ma, frequency

        self.clamping_active = False
        return amplitude, frequency

    def mitigate_signal_anomalies(self, data: np.ndarray, anomalies: List[str]) -> np.ndarray:
        with self._lock:
            return self._mitigate_signal_anomalies(data, anomalies)

    def _mitigate_signal_anomalies(self, data: np.ndarray, anomalies: List[str]) -> np.ndarray:
        """
        Active channel filtering and reconstruction.
        Mutes anomalous channels and fills with baseline noise to keep decoder stable.
        """
        clean_data = data.copy()
        muted_channels: list[int] = []

        if "DATA_CORRUPTION_ANOMALY" in anomalies:
            # Replace all NaN values with zeros across all channels to prevent autoencoder crash
            clean_data = np.nan_to_num(clean_data, nan=0.0)
            muted_channels.extend(range(clean_data.shape[0]))
            self.blocked_attacks_count += 1
            if self.event_bus:
                self.event_bus.publish(Event(
                    topic="ips.channels_muted",
                    data={
                        "muted_channels": muted_channels,
                        "reason": "DATA_CORRUPTION_ANOMALY",
                        "sim_clock": self.twin.get_sim_clock()
                    },
                    source="ips"
                ))
            return clean_data

        if "HIGH_NOISE_ANOMALY" in anomalies or "SIGNAL_SUPPRESSION_ANOMALY" in anomalies:
            # Filter and replace abnormal channels with low-amplitude nominal noise
            for ch in range(clean_data.shape[0]):
                ch_signal = clean_data[ch, :]
                rms = calculate_rms(ch_signal)
                if rms > self.ids.rms_high_threshold or rms < self.ids.rms_low_threshold:
                    # Replace anomalous signal with 0.0 to prevent cascade false positives
                    clean_data[ch, :] = np.zeros(clean_data.shape[1])
                    muted_channels.append(ch)

            if muted_channels:
                self.blocked_attacks_count += 1
                if self.event_bus:
                    self.event_bus.publish(Event(
                        topic="ips.channels_muted",
                        data={
                            "muted_channels": muted_channels,
                            "sim_clock": self.twin.get_sim_clock()
                        },
                        source="ips"
                    ))

        return clean_data

    def mitigate_pathological_sync(self, anomalies: List[str]) -> bool:
        with self._lock:
            return self._mitigate_pathological_sync(anomalies)

    def _mitigate_pathological_sync(self, anomalies: List[str]) -> bool:
        """
        Detects closed-loop phase-locked stimulation compromise and suspends therapy
        gracefully to prevent tremor amplification.
        """
        if "PATHOLOGICAL_SYNCHRONIZATION_ATTACK" in anomalies:
            self.blocked_attacks_count += 1
            if self.twin.fallback_mode_enabled:
                # Transition to Safe open-loop Fallback Therapy mode
                self.twin.enable_fallback_mode(True)
                self.twin.set_clinical_alert(True, "Degraded (Safe Fallback)")
                self.twin.update_decoder_confidence(0.90)  # Recover confidence partially
                self.twin.update_clinical_risk(
                    hazard_state="NOMINAL",  # Patient is clinically protected
                    iso_severity="MARGINAL",
                    tissue_damage_risk="NONE",
                    clinical_action="OPEN_LOOP_FALLBACK"
                )
            else:
                # Legacy behavior: Force safety shutoff of stimulator to suspend compromised closed-loop
                self.twin.update_therapy(False)
                self.twin.update_stimulation_params(0.0, 0.0)
                self.twin.set_clinical_alert(True, "IDS Suspend: Sync Detected")
                self.twin.update_decoder_confidence(0.90)  # Recover confidence partially
                self.twin.update_clinical_risk(
                    hazard_state="THERAPY_SUSPENDED",
                    iso_severity="MARGINAL",
                    tissue_damage_risk="NONE",
                    clinical_action="SUSPEND_THERAPY"
                )

            if self.event_bus:
                self.event_bus.publish(Event(
                    topic="ips.dbs_sync_mitigated",
                    data={
                        "clinical_status": "IDS Suspend: Sync Detected",
                        "fallback_mode": self.twin.fallback_mode_enabled,
                        "sim_clock": self.twin.get_sim_clock()
                    },
                    source="ips"
                ))
            return True
        return False


class BLELinkGuard:
    """
    BLE Link Layer Guard.
    Prevents link-level boundary abuses and illegal MTU negotiations.
    """

    def __init__(self, twin: DigitalTwin, event_bus: Optional[EventBus] = None):
        self.twin = twin
        self.event_bus = event_bus
        self.blocked_mtu_abuses = 0
        self.jamming_alerts = 0
        self.blocked_spoofing_attempts = 0
        self._lock = threading.RLock()

    def verify_connection(self, client_mac: str, is_paired: bool, bonding_db: dict) -> bool:
        with self._lock:
            return self._verify_connection(client_mac, is_paired, bonding_db)

    def _verify_connection(self, client_mac: str, is_paired: bool, bonding_db: dict) -> bool:
        """
        Defends against BLESA (BLE Spoofing Attack).
        Requires devices with known MAC addresses to prove they possess the IRK/LTK (via is_paired).
        If a device MAC is in bonding_db but is_paired is False, it's a spoofing attempt.
        """
        if client_mac in bonding_db:
            if not is_paired:
                self.blocked_spoofing_attempts += 1
                self.twin.set_clinical_alert(True, f"BLE Link Guard: Blocked Spoofing (BLESA) from {client_mac}")
                if self.event_bus:
                    self.event_bus.publish(Event(
                        topic="link_guard.spoofing_blocked",
                        data={"mac": client_mac, "sim_clock": self.twin.get_sim_clock()},
                        source="link_guard"
                    ))
                return False
        return True

    def check_rf_environment(self):
        with self._lock:
            return self._check_rf_environment()

    def _check_rf_environment(self):
        drop_rate = getattr(self.twin, "rf_packet_drop_rate", 0.0)
        # If dropping more than 30% of packets, trigger RF Jamming Alert
        if drop_rate >= BLEConstants.JAMMING_DROP_RATE_THRESHOLD:
            self.jamming_alerts += 1
            self.twin.set_clinical_alert(True, f"BLE Link Guard: Severe RF Jamming Detected ({drop_rate*100:.0f}% drops)")
            if self.event_bus:
                self.event_bus.publish(Event(
                    topic="link_guard.jamming_detected",
                    data={"drop_rate": drop_rate, "sim_clock": self.twin.get_sim_clock()},
                    source="link_guard"
                ))

    def verify_mtu(self, requested_mtu: int) -> int:
        with self._lock:
            return self._verify_mtu(requested_mtu)

    def _verify_mtu(self, requested_mtu: int) -> int:
        # BLE specification minimum MTU size is 23 bytes, maximum is 512 bytes (BLE 5.2)
        if requested_mtu < BLEConstants.MIN_MTU_SIZE or requested_mtu > BLEConstants.MAX_MTU_SIZE:
            self.blocked_mtu_abuses += 1
            self.twin.set_clinical_alert(True, "BLE Link Guard: Blocked MTU Abuse")

            if self.event_bus:
                self.event_bus.publish(Event(
                    topic="link_guard.mtu_abuse_blocked",
                    data={
                        "requested_mtu": requested_mtu,
                        "enforced_mtu": BLEConstants.MIN_MTU_SIZE,
                        "sim_clock": self.twin.get_sim_clock()
                    },
                    source="link_guard"
                ))

            # Enforce spec limits
            return max(BLEConstants.MIN_MTU_SIZE, min(requested_mtu, BLEConstants.MAX_MTU_SIZE))
        return requested_mtu
