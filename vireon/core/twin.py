import threading
from typing import Dict, Any, List
import numpy as np
import os
import json
from collections import deque
from vireon.core.physics import PhysicsEngine
from vireon.core.dynamics import KuramotoModel
import logging

logger = logging.getLogger(__name__)


from vireon.core.interfaces import ITwin

class DigitalTwin(ITwin):
    """
    Authoritative source of truth for a simulated neurodevice.

    Every simulated event modifies the Digital Twin. All subsystems
    read from and write to this single state container.
    """

    def __init__(self, device_id: str = "virtual_openbci_board",
                 sample_rate: int = 250, num_channels: int = 8, hardware_mode: bool = False, seed: Optional[int] = None):
        self._lock = threading.RLock()
        
        self.physics_engine = PhysicsEngine()
        self.hardware_mode = hardware_mode

        # Core State Variables
        self.device_id = device_id
        self.connected = True
        self.battery_level = 100.0
        self.firmware_version = "1.0.0-shield"
        self.sample_rate = sample_rate
        self.num_channels = num_channels

        # Initialize electrode impedances to nominal (5.0 kOhms)
        self.electrode_impedances: Dict[int, float] = {i: 5.0 for i in range(num_channels)}

        # Therapy & Stimulation parameters
        self.stimulation_enabled = False
        self.stimulation_amplitude_ma = 0.0
        self.stimulation_frequency_hz = 0.0
        
        # Safe Fallback Therapy Mode (Paradox 2 solution)
        self.fallback_mode_enabled = False
        self.fallback_mode_active = False
        self.fallback_amplitude_ma = 1.5
        self.fallback_frequency_hz = 130.0

        # Clinical variables
        self.decoder_confidence = 1.0
        self.clinical_alert_active = False
        self.clinical_status = "Nominal"
        self.hazard_state = "NOMINAL"
        self.iso_severity = "NEGLIGIBLE"
        self.tissue_damage_risk = "NONE"
        self.clinical_action = "MONITOR"
        self.dsm5_diagnosis = "UNKNOWN"
        self.diagnostic_cluster = "UNKNOWN"
        self.niss_score = 0.0

        # Active configuration state (can be modified by UI)
        self.dbs_mode = False
        self.secure_mode = False
        self.nsp_mode = False
        self.e2ee_mode = False
        self.active_attack = "none"

        # Extended state variables (Phase 1 additions)
        self.temperature_celsius = 37.0       # Device/tissue temperature
        self.flash_utilization_pct = 0.0      # Internal flash usage
        self.memory_usage_pct = 0.0           # RAM usage
        self.ble_pairing_state = "UNPAIRED"   # "UNPAIRED", "PAIRING", "PAIRED", "BONDED"
        self.communication_sessions = 0       # Active communication session count
        self.amplifier_saturated = False
        
        # ADC Hardware Profile
        self.adc_vref = 4.5
        self.adc_gain = 24.0
        self.adc_resolution_bits = 24
        self.amplifier_gain = 24              # ADS1299 default gain
        
        # OSI of Mind (Threat Atlas) Additions
        self.funnel_origin = "Ring 4: Cortical"
        self.autonomic_pupil_dilation_mm = 4.0 # Baseline pupil dilation in mm
        self.brain_regions: Dict[str, Any] = {}
        self.channel_to_region: Dict[str, Any] = {}
        self._load_atlas_mapping()

        # Continuous ODE Dynamics
        self.neural_dynamics = KuramotoModel(num_oscillators=self.num_channels, seed=seed)

        # Simulation clock (monotonic, not wall-clock)
        self._sim_clock: float = 0.0

        # History log for reporting (capped to prevent memory leak)
        self.history = deque(maxlen=1000)

        # Log initial state
        self._log_state_change("Initialization")

    def _load_atlas_mapping(self):
        """Loads Threat Atlas to map device channels to brain regions."""
        try:
            atlas_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), 
                "../../neurosecurity/datalake/threat-atlas-brain-bci.json"
            ))
            if os.path.exists(atlas_path):
                with open(atlas_path, "r", encoding="utf-8") as f:
                    self.atlas_data = json.load(f)
                    for region in self.atlas_data.get("brain_regions", []):
                        self.brain_regions[region["id"]] = region
                    self.channel_to_region = self.atlas_data.get("mappings", {})
            else:
                self.channel_to_region = {}
        except Exception as e:
            logger.warning(f"Failed to load Threat Atlas. Running without anatomical mapping: {e}")
            self.channel_to_region = {}

    # --- Simulation Clock & Battery Sag Emulation ---

    def set_sim_clock(self, t: float):
        """Set the simulation clock. Called by the ReplayEngine each tick."""
        with self._lock:
            dt = t - self._sim_clock
            self._sim_clock = t
            if dt > 0:
                self._tick_battery_locked(dt)

    def _tick_battery_locked(self, dt: float):
        """Simulate battery discharge and voltage sag under load (running within lock).
        Uses Peukert's Law for non-linear capacity reduction under high load.
        """
        # 1. Base current draw (mA)
        base_ma = 5.0
        
        # 2. Stimulation current draw (mA)
        stim_ma = 0.0
        if self.stimulation_enabled and self.stimulation_amplitude_ma > 0:
            stim_ma = self.stimulation_amplitude_ma * (self.stimulation_frequency_hz / 130.0) * 2.0
            
        total_ma = base_ma + stim_ma
        
        # Peukert's Law: Effective current = I^k (k ~ 1.2 for medical batteries)
        peukert_k = 1.2
        effective_ma = total_ma ** peukert_k
        
        # Calibrate so base_ma matches previous base_draw of 0.005 %/sec
        capacity_scaling = 0.005 / (base_ma ** peukert_k)
        
        total_draw_pct = effective_ma * capacity_scaling * dt
        self.battery_level = max(0.0, self.battery_level - total_draw_pct)
        
        # 3. Physically consistent battery model: V = OCV(SoC) - I * R_int
        # OCV (Open Circuit Voltage) roughly 3.0V (0%) to 4.2V (100%)
        ocv_v = 3.0 + 1.2 * (self.battery_level / 100.0)
        
        # Internal resistance (Ohms). Increases as SoC drops.
        r_int_ohms = 0.5 + 2.0 * (1.0 - (self.battery_level / 100.0))
        
        # Voltage drop under load
        v_drop = (total_ma / 1000.0) * r_int_ohms
        effective_voltage_v = ocv_v - v_drop
        
        # Convert back to an "effective percentage" for the brownout logic (approx 3.15V cutoff ~ 5%)
        effective_voltage_pct = max(0.0, (effective_voltage_v - 3.15) / 1.05 * 100.0)
        
        if effective_voltage_pct < 5.0 and self.connected:
            self.connected = False
            self.stimulation_enabled = False
            self.stimulation_amplitude_ma = 0.0
            self.stimulation_frequency_hz = 0.0
            self.clinical_alert_active = True
            self.clinical_status = "Brownout: Voltage Sag Reset"
            self.hazard_state = "BROWNOUT"
            self.iso_severity = "CRITICAL"
            self._log_state_change("Brownout: Device shut down due to voltage sag under stimulation load")

    def get_sim_clock(self) -> float:
        """Return the current simulation clock value."""
        return self._sim_clock

    # --- State Accessors ---

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "device_id": self.device_id,
                "connected": self.connected,
                "battery_level": round(self.battery_level, 2),
                "firmware_version": self.firmware_version,
                "sample_rate": self.sample_rate,
                "num_channels": self.num_channels,
                "electrode_impedances": {str(k): round(v, 2) for k, v in self.electrode_impedances.items()},
                "stimulation_enabled": self.stimulation_enabled,
                "stimulation_amplitude_ma": round(self.stimulation_amplitude_ma, 2),
                "stimulation_frequency_hz": round(self.stimulation_frequency_hz, 2),
                "decoder_confidence": round(self.decoder_confidence, 2),
                "clinical_alert_active": self.clinical_alert_active,
                "clinical_status": self.clinical_status,
                "hazard_state": self.hazard_state,
                "iso_severity": self.iso_severity,
                "tissue_damage_risk": self.tissue_damage_risk,
                "clinical_action": self.clinical_action,
                "dsm5_diagnosis": self.dsm5_diagnosis,
                "diagnostic_cluster": self.diagnostic_cluster,
                "niss_score": self.niss_score,
                # Extended state
                "temperature_celsius": round(self.temperature_celsius, 1),
                "flash_utilization_pct": round(self.flash_utilization_pct, 1),
                "memory_usage_pct": round(self.memory_usage_pct, 1),
                "ble_pairing_state": self.ble_pairing_state,
                "amplifier_gain": self.amplifier_gain,
                "communication_sessions": self.communication_sessions,
                "funnel_origin": self.funnel_origin,
                "autonomic_pupil_dilation_mm": round(self.autonomic_pupil_dilation_mm, 2),
                "sim_clock": round(self._sim_clock, 3),
                "neural_coherence": round(self.neural_dynamics.coherence, 3),
                "beta_power": round(self.neural_dynamics.beta_power, 2),
            }

    # --- Snapshot / Restore (for experiment reproducibility) ---

    def snapshot(self) -> Dict[str, Any]:
        """
        Return a complete frozen state copy suitable for serialization.
        Used to save/restore experiment states for reproducibility.
        """
        with self._lock:
            return {
                "device_id": self.device_id,
                "connected": self.connected,
                "battery_level": self.battery_level,
                "firmware_version": self.firmware_version,
                "sample_rate": self.sample_rate,
                "num_channels": self.num_channels,
                "electrode_impedances": dict(self.electrode_impedances),
                "stimulation_enabled": self.stimulation_enabled,
                "stimulation_amplitude_ma": self.stimulation_amplitude_ma,
                "stimulation_frequency_hz": self.stimulation_frequency_hz,
                "decoder_confidence": self.decoder_confidence,
                "clinical_alert_active": self.clinical_alert_active,
                "clinical_status": self.clinical_status,
                "hazard_state": self.hazard_state,
                "iso_severity": self.iso_severity,
                "tissue_damage_risk": self.tissue_damage_risk,
                "clinical_action": self.clinical_action,
                "dsm5_diagnosis": self.dsm5_diagnosis,
                "diagnostic_cluster": self.diagnostic_cluster,
                "niss_score": self.niss_score,
                "temperature_celsius": self.temperature_celsius,
                "flash_utilization_pct": self.flash_utilization_pct,
                "memory_usage_pct": self.memory_usage_pct,
                "ble_pairing_state": self.ble_pairing_state,
                "amplifier_gain": self.amplifier_gain,
                "communication_sessions": self.communication_sessions,
                "funnel_origin": self.funnel_origin,
                "autonomic_pupil_dilation_mm": self.autonomic_pupil_dilation_mm,
                "fallback_mode_enabled": self.fallback_mode_enabled,
                "fallback_mode_active": self.fallback_mode_active,
                "sim_clock": self._sim_clock,
                "neural_dynamics": self.neural_dynamics.get_state() if hasattr(self.neural_dynamics, 'get_state') else None,
                "neural_coherence": self.neural_dynamics.coherence,
                "beta_power": self.neural_dynamics.beta_power,
                "history": list(self.history),
            }

    def restore(self, snap: Dict[str, Any]):
        """
        Restore state from a snapshot. Used for experiment replay.
        """
        with self._lock:
            self.device_id = snap.get("device_id", self.device_id)
            self.connected = snap.get("connected", self.connected)
            self.battery_level = snap.get("battery_level", self.battery_level)
            self.firmware_version = snap.get("firmware_version", self.firmware_version)
            self.sample_rate = snap.get("sample_rate", self.sample_rate)
            self.num_channels = snap.get("num_channels", self.num_channels)
            self.electrode_impedances = snap.get("electrode_impedances", self.electrode_impedances)
            self.stimulation_enabled = snap.get("stimulation_enabled", self.stimulation_enabled)
            self.stimulation_amplitude_ma = snap.get("stimulation_amplitude_ma", self.stimulation_amplitude_ma)
            self.stimulation_frequency_hz = snap.get("stimulation_frequency_hz", self.stimulation_frequency_hz)
            self.decoder_confidence = snap.get("decoder_confidence", self.decoder_confidence)
            self.clinical_alert_active = snap.get("clinical_alert_active", self.clinical_alert_active)
            self.clinical_status = snap.get("clinical_status", self.clinical_status)
            self.hazard_state = snap.get("hazard_state", self.hazard_state)
            self.iso_severity = snap.get("iso_severity", self.iso_severity)
            self.tissue_damage_risk = snap.get("tissue_damage_risk", self.tissue_damage_risk)
            self.clinical_action = snap.get("clinical_action", self.clinical_action)
            self.dsm5_diagnosis = snap.get("dsm5_diagnosis", self.dsm5_diagnosis)
            self.diagnostic_cluster = snap.get("diagnostic_cluster", self.diagnostic_cluster)
            self.niss_score = snap.get("niss_score", self.niss_score)
            self.temperature_celsius = snap.get("temperature_celsius", self.temperature_celsius)
            self.flash_utilization_pct = snap.get("flash_utilization_pct", self.flash_utilization_pct)
            self.memory_usage_pct = snap.get("memory_usage_pct", self.memory_usage_pct)
            self.ble_pairing_state = snap.get("ble_pairing_state", self.ble_pairing_state)
            self.amplifier_gain = snap.get("amplifier_gain", 24)
            self.communication_sessions = snap.get("communication_sessions", 0)
            self.funnel_origin = snap.get("funnel_origin", "Ring 4: Cortical")
            self.autonomic_pupil_dilation_mm = snap.get("autonomic_pupil_dilation_mm", 4.0)
            
            self.fallback_mode_enabled = snap.get("fallback_mode_enabled", self.fallback_mode_enabled)
            self.fallback_mode_active = snap.get("fallback_mode_active", self.fallback_mode_active)
            if "neural_dynamics" in snap and snap["neural_dynamics"] is not None:
                if hasattr(self.neural_dynamics, 'restore_state'):
                    self.neural_dynamics.restore_state(snap["neural_dynamics"])
                
            # Keep history as deque
            if "history" in snap:
                self.history = deque(snap["history"], maxlen=1000)
                
            self._sim_clock = snap.get("sim_clock", self._sim_clock)

    # --- State Mutators ---

    def _log_state_change(self, event: str):
        # Always run within lock or call from locked context
        state_copy = {
            "timestamp": self._sim_clock,
            "event": event,
            "connected": self.connected,
            "battery_level": self.battery_level,
            "electrode_impedances": self.electrode_impedances.copy(),
            "stimulation_enabled": self.stimulation_enabled,
            "stimulation_amplitude_ma": self.stimulation_amplitude_ma,
            "stimulation_frequency_hz": self.stimulation_frequency_hz,
            "decoder_confidence": self.decoder_confidence,
            "clinical_alert_active": self.clinical_alert_active,
            "clinical_status": self.clinical_status,
            "hazard_state": self.hazard_state,
            "iso_severity": self.iso_severity,
            "tissue_damage_risk": self.tissue_damage_risk,
            "clinical_action": self.clinical_action,
            "dsm5_diagnosis": self.dsm5_diagnosis,
            "diagnostic_cluster": self.diagnostic_cluster,
            "niss_score": self.niss_score
        }
        self.history.append(state_copy)

    def simulate_adc_saturation(self, data: np.ndarray) -> np.ndarray:
        """
        Simulates ADS1299 ADC input amplifier saturation.
        Clamps inputs exceeding +-1000 uV to rail limits and logs error state.
        """
        import numpy as np
        saturated = bool(np.any(np.abs(data) >= 1000.0))
        
        with self._lock:
            if saturated != self.amplifier_saturated:
                self.amplifier_saturated = saturated
                if saturated:
                    self.clinical_alert_active = True
                    self.clinical_status = "Amplifier Saturation Error"
                    self.hazard_state = "AMPLIFIER_SATURATED"
                    self.iso_severity = "CRITICAL"
                    self._log_state_change("ADC Saturation: Dynamic range limit exceeded, signal clipped to rails.")
                else:
                    self.clinical_alert_active = False
                    self.clinical_status = "Nominal"
                    self.hazard_state = "NOMINAL"
                    self.iso_severity = "NEGLIGIBLE"
                    self._log_state_change("ADC Saturation: Dynamic range recovered.")
                    
        if saturated:
            return np.clip(data, -1000.0, 1000.0)
        return data

    def verify_electrode_connection(self, signal_data: np.ndarray) -> bool:
        """
        Active biosensing check using signal quality.
        Detects signal spoofing and contact status based on signal variance.
        Note: This is a signal-quality heuristic, not a true electrical impedance measurement.
        """
        import numpy as np
        channel_vars = np.var(signal_data, axis=1)
        
        with self._lock:
            for ch in range(self.num_channels):
                var = channel_vars[ch]
                if var > 100000.0:
                    val = 60.0
                elif var < 0.1:
                    val = 100.0
                else:
                    val = 5.0
                
                if ch in self.electrode_impedances:
                    if abs(self.electrode_impedances[ch] - val) > 0.01:
                        self.electrode_impedances[ch] = val
                        self._log_state_change(f"Active Probe Impedance check: ch {ch} -> {val:.2f} kOhm")
                        
            return all(2.0 <= imp <= 15.0 for imp in self.electrode_impedances.values())

    def update_impedance(self, ch: int, val: float):
        with self._lock:
            if ch in self.electrode_impedances:
                old_val = self.electrode_impedances[ch]
                if abs(old_val - val) > 0.01:
                    self.electrode_impedances[ch] = val
                    self._log_state_change(f"Impedance update: ch {ch} -> {val:.2f} kOhm")

    def set_connection(self, status: bool):
        with self._lock:
            if self.connected != status:
                self.connected = status
                self._log_state_change(f"Connection status changed to: {status}")

    def update_decoder_confidence(self, conf: float):
        with self._lock:
            # Clip between 0.0 and 1.0
            conf = max(0.0, min(1.0, conf))
            if abs(self.decoder_confidence - conf) > 0.01:
                self.decoder_confidence = conf
                self._log_state_change(f"Decoder confidence updated: {conf:.2f}")

    def enable_fallback_mode(self, active: bool):
        with self._lock:
            if self.fallback_mode_active != active:
                self.fallback_mode_active = active
                if active:
                    self.stimulation_enabled = True
                    self.stimulation_amplitude_ma = self.fallback_amplitude_ma
                    self.stimulation_frequency_hz = self.fallback_frequency_hz
                    self.clinical_status = "Degraded (Safe Fallback)"
                    self._log_state_change("Safe Fallback Mode Activated")
                else:
                    self.clinical_status = "Nominal"
                    self._log_state_change("Safe Fallback Mode Deactivated")

    def update_therapy(self, enabled: bool):
        with self._lock:
            if self.fallback_mode_active:
                self.stimulation_enabled = True
                return
            if self.stimulation_enabled != enabled:
                self.stimulation_enabled = enabled
                self._log_state_change(f"Stimulation therapy {'enabled' if enabled else 'disabled'}")

    def update_stimulation_params(self, amplitude: float, frequency: float):
        with self._lock:
            if self.fallback_mode_active:
                self.stimulation_amplitude_ma = self.fallback_amplitude_ma
                self.stimulation_frequency_hz = self.fallback_frequency_hz
                return
            if self.stimulation_amplitude_ma != amplitude or self.stimulation_frequency_hz != frequency:
                self.stimulation_amplitude_ma = amplitude
                self.stimulation_frequency_hz = frequency
                self._log_state_change(f"Stimulation parameters updated: {amplitude} mA @ {frequency} Hz")

    def update_clinical_status(self, status: str, alert: bool = False, hazard: str = "NOMINAL", iso: str = "NEGLIGIBLE", action: str = "MONITOR"):
        with self._lock:
            if self.clinical_alert_active != alert or self.clinical_status != status:
                self.clinical_alert_active = alert
                self.clinical_status = status
                self.hazard_state = hazard
                self.iso_severity = iso
                self.clinical_action = action
                self._log_state_change(f"Clinical alert status: active={alert}, status={status}")

    def set_clinical_alert(self, active: bool, message: str):
        """Helper to quickly set a clinical alert status."""
        self.update_clinical_status(status=message, alert=active, hazard="WARNING" if active else "NOMINAL", iso="MARGINAL" if active else "NEGLIGIBLE")

    def update_battery(self, level: float):
        with self._lock:
            level = max(0.0, min(100.0, level))
            if abs(self.battery_level - level) > 0.1:
                self.battery_level = level
                self._log_state_change(f"Battery level: {level:.1f}%")

    def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.history)

    def update_clinical_risk(self, hazard_state: str, iso_severity: str, tissue_damage_risk: str, clinical_action: str,
                             dsm5_diagnosis: str = "UNKNOWN", diagnostic_cluster: str = "UNKNOWN", niss_score: float = 0.0):
        with self._lock:
            if (self.hazard_state != hazard_state or
                self.iso_severity != iso_severity or
                self.tissue_damage_risk != tissue_damage_risk or
                self.clinical_action != clinical_action or
                self.dsm5_diagnosis != dsm5_diagnosis or
                self.diagnostic_cluster != diagnostic_cluster or
                self.niss_score != niss_score):

                self.hazard_state = hazard_state
                self.iso_severity = iso_severity
                self.tissue_damage_risk = tissue_damage_risk
                self.clinical_action = clinical_action
                self.dsm5_diagnosis = dsm5_diagnosis
                self.diagnostic_cluster = diagnostic_cluster
                self.niss_score = niss_score
                self._log_state_change(f"Clinical risk updated: state={hazard_state}, severity={iso_severity}, dsm5={dsm5_diagnosis}")

    # --- Extended State Mutators ---

    def update_temperature(self, temp_c: float):
        with self._lock:
            if abs(self.temperature_celsius - temp_c) > 0.05:
                self.temperature_celsius = temp_c
                self._log_state_change(f"Temperature: {temp_c:.1f}°C")

    def update_ble_pairing_state(self, state: str):
        with self._lock:
            if self.ble_pairing_state != state:
                self.ble_pairing_state = state
                self._log_state_change(f"BLE pairing state: {state}")
