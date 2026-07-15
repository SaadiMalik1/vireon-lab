import json
import os
import logging
from typing import Any
from dataclasses import dataclass

@dataclass
class ThermodynamicConstants:
    """
    Thermodynamic parameters for the Pennes Bioheat Equation (Lumped Approximation).
    References:
    - Pennes, H. H. (1948). Analysis of tissue and arterial blood temperatures in the resting human forearm.
    - Elwassif, M. M., et al. (2006). Bioheat transfer model of deep brain stimulation.
    """
    rho_c: float = 3.6e6            # Tissue volumetric heat capacity (J/m^3K)
    w_b_rho_b_c_b: float = 40000.0  # Blood perfusion term (W/m^3K)
    Q_m: float = 10000.0            # Metabolic heat generation (W/m^3)
    vol_m3: float = 1.5e-9          # Assumed heated volume 1.5 mm^3
    pulse_width_s: float = 100e-6   # Default pulse width

logger = logging.getLogger("PhysicsEngine")

class PhysicsEngine:
    """
    Thermodynamic and electrochemical limits engine.
    Loads actual BCI physical constraints from threat_atlas.json and applies them to the DigitalTwin.
    """
    def __init__(self):
        self.thermo_const = ThermodynamicConstants()
        self.max_temp_rise_c = 1.0     # Default fallback
        self.max_dc_leakage_ua = 0.4   # Default fallback
        self._load_atlas_constants()

    def _load_atlas_constants(self):
        atlas_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins", "clinical", "data", "threat_atlas.json")
        if not os.path.exists(atlas_path):
            logger.warning("threat_atlas.json not found offline, using fallback physics constants.")
            return

        try:
            with open(atlas_path, "r", encoding="utf-8") as f:
                atlas_data = json.load(f)
            
            constants = atlas_data.get("physics", {}).get("constants", [])
            for c in constants:
                if c.get("parameter") == "Max safe tissue temp rise":
                    # Parse "1.0°C" -> 1.0
                    val_str = str(c.get("value", "")).replace("°C", "").strip()
                    try:
                        self.max_temp_rise_c = float(val_str)
                    except ValueError as e:
                        logger.warning(f"Failed to parse Max safe tissue temp rise: {e}")
                elif c.get("parameter") == "DC leakage tissue damage threshold":
                    # Parse "0.4 µA" -> 0.4
                    val_str = str(c.get("value", "")).replace("µA", "").strip()
                    try:
                        self.max_dc_leakage_ua = float(val_str)
                    except ValueError as e:
                        logger.warning(f"Failed to parse DC leakage tissue damage threshold: {e}")
            logger.info(f"Loaded Physics Constants: MaxTempRise={self.max_temp_rise_c}°C, MaxLeakage={self.max_dc_leakage_ua}µA")
        except Exception as e:
            logger.error(f"Error parsing threat_atlas.json for physics constants: {e}")

    def tick(self, twin: Any, dt: float):
        """
        Evaluate physical constraints over time interval dt.
        """
        # Calculate Thermodynamic tissue heating using Pennes Bioheat Equation
        # Pennes Bioheat Equation (Lumped Approximation)
        T_a = 37.0 - (self.thermo_const.Q_m / self.thermo_const.w_b_rho_b_c_b) # Calibrated arterial blood temp to keep equilibrium at 37.0
        
        Q_ext = 0.0
        if twin.stimulation_enabled and twin.stimulation_amplitude_ma > 0:
            # Joule heating: P = I^2 * R * duty_cycle
            I_A = twin.stimulation_amplitude_ma * 1e-3
            R_ohms = twin.electrode_impedances.get(0, 5.0) * 1000.0
            duty_cycle = twin.stimulation_frequency_hz * self.thermo_const.pulse_width_s
            power_W = (I_A ** 2) * R_ohms * duty_cycle
            Q_ext = power_W / self.thermo_const.vol_m3
            
        def get_dT_dt(T):
            return (self.thermo_const.w_b_rho_b_c_b * (T_a - T) + self.thermo_const.Q_m + Q_ext) / self.thermo_const.rho_c

        # RK4 Integration for stability
        k1 = get_dT_dt(twin.temperature_celsius)
        k2 = get_dT_dt(twin.temperature_celsius + 0.5 * dt * k1)
        k3 = get_dT_dt(twin.temperature_celsius + 0.5 * dt * k2)
        k4 = get_dT_dt(twin.temperature_celsius + dt * k3)
        
        dT_total = (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4)
        twin.temperature_celsius = max(37.0, twin.temperature_celsius + dT_total)
        
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
                if twin.hazard_state != "WARNING" or twin.iso_severity != "HIGH":
                    twin.clinical_status = f"Physics Violation (Sim): {violation_msg}"
                    twin.hazard_state = "WARNING"
                    twin.iso_severity = "HIGH"
                    twin._log_state_change(twin.clinical_status)
        else:
            # Decay risk if we're back in safe margins and it was high just from physics
            if twin.tissue_damage_risk == "HIGH" and twin.hazard_state == "WARNING":
                twin.tissue_damage_risk = "NONE"
                twin.clinical_alert_active = False
                twin.clinical_status = "Nominal"
                twin.hazard_state = "NOMINAL"
                twin.iso_severity = "NEGLIGIBLE"
                twin._log_state_change("Physics states returned to nominal")
