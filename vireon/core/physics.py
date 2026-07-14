import json
import os
import logging
from typing import Any

logger = logging.getLogger("PhysicsEngine")

class PhysicsEngine:
    """
    Thermodynamic and electrochemical limits engine.
    Loads actual BCI physical constraints from qif.json and applies them to the DigitalTwin.
    """
    def __init__(self):
        self.max_temp_rise_c = 1.0     # Default fallback
        self.max_dc_leakage_ua = 0.4   # Default fallback
        self._load_qif_constants()

    def _load_qif_constants(self):
        qif_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins", "clinical", "data", "qif.json")
        if not os.path.exists(qif_path):
            logger.warning("qif.json not found offline, using fallback physics constants.")
            return

        try:
            with open(qif_path, "r", encoding="utf-8") as f:
                qif_data = json.load(f)
            
            constants = qif_data.get("physics", {}).get("constants", [])
            for c in constants:
                if c.get("parameter") == "Max safe tissue temp rise":
                    # Parse "1.0°C" -> 1.0
                    val_str = str(c.get("value", "")).replace("°C", "").strip()
                    try:
                        self.max_temp_rise_c = float(val_str)
                    except ValueError:
                        pass
                elif c.get("parameter") == "DC leakage tissue damage threshold":
                    # Parse "0.4 µA" -> 0.4
                    val_str = str(c.get("value", "")).replace("µA", "").strip()
                    try:
                        self.max_dc_leakage_ua = float(val_str)
                    except ValueError:
                        pass
            logger.info(f"Loaded Physics Constants: MaxTempRise={self.max_temp_rise_c}°C, MaxLeakage={self.max_dc_leakage_ua}µA")
        except Exception as e:
            logger.error(f"Error parsing qif.json for physics constants: {e}")

    def tick(self, twin: Any, dt: float):
        """
        Evaluate physical constraints over time interval dt.
        """
        # Calculate Thermodynamic tissue heating
        # Heating is proportional to amplitude squared and frequency
        if twin.stimulation_enabled and twin.stimulation_amplitude_ma > 0:
            heating_rate = 0.0001 * (twin.stimulation_amplitude_ma ** 2) * twin.stimulation_frequency_hz
        else:
            heating_rate = 0.0
            
        temp_delta = (heating_rate - 0.05 * (twin.temperature_celsius - 37.0)) * dt
        twin.temperature_celsius = max(37.0, twin.temperature_celsius + temp_delta)
        
        # Calculate theoretical DC leakage
        # Simplified heuristic: high amplitude/frequency causes imperfect charge balancing leading to leakage
        if twin.stimulation_enabled and twin.stimulation_amplitude_ma > 0:
            leakage_ua = 0.1 * twin.stimulation_amplitude_ma * (twin.stimulation_frequency_hz / 130.0)
        else:
            leakage_ua = 0.0

        # Check violations
        temp_rise = twin.temperature_celsius - 37.0
        
        violation_msg = None
        if temp_rise > self.max_temp_rise_c:
            violation_msg = f"Tissue temp rise limit exceeded: {temp_rise:.2f}°C > {self.max_temp_rise_c}°C"
        elif leakage_ua > self.max_dc_leakage_ua:
            violation_msg = f"DC leakage limit exceeded: {leakage_ua:.2f}µA > {self.max_dc_leakage_ua}µA"

        if violation_msg:
            if getattr(twin, "hardware_mode", False):
                # Hard Hardware Failsafe
                twin.stimulation_enabled = False
                twin.stimulation_amplitude_ma = 0.0
                twin.stimulation_frequency_hz = 0.0
                twin.hazard_state = "HARDWARE_SHUTDOWN"
                twin.iso_severity = "CRITICAL"
                twin.clinical_alert_active = True
                twin.clinical_status = f"Hardware Failsafe: {violation_msg}"
                twin._log_state_change(twin.clinical_status)
            else:
                # Simulation Warning Mode
                twin.tissue_damage_risk = "HIGH"
                twin.clinical_alert_active = True
                if twin.clinical_status == "Nominal" or "Physics Violation" not in twin.clinical_status:
                    twin.clinical_status = f"Physics Violation (Sim): {violation_msg}"
                    twin.hazard_state = "WARNING"
                    twin.iso_severity = "HIGH"
                    twin._log_state_change(twin.clinical_status)
        else:
            # Decay risk if we're back in safe margins and it was high just from physics
            if twin.tissue_damage_risk == "HIGH" and "Physics Violation" in twin.clinical_status:
                twin.tissue_damage_risk = "NONE"
                twin.clinical_alert_active = False
                twin.clinical_status = "Nominal"
                twin.hazard_state = "NOMINAL"
                twin.iso_severity = "NEGLIGIBLE"
                twin._log_state_change("Physics states returned to nominal")
