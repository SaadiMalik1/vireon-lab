"""
Closed-Loop Safety Envelope (IEC 62304 / ISO 14971).

Defines the safe operational bounds for neurostimulation. If the
implanted device's parameters (amplitude, frequency, temperature,
charge density) drift outside this mathematical envelope, the
system must automatically fallback to a safe mode.
"""

from typing import Dict, Any, Tuple
from vireon.core.twin import DigitalTwin

class SafetyEnvelope:
    def __init__(self, 
                 max_amplitude_ma: float = 5.0, 
                 max_frequency_hz: float = 160.0, 
                 max_temperature_c: float = 39.0,
                 max_charge_density_uc_cm2: float = 30.0):
        self.max_amplitude = max_amplitude_ma
        self.max_frequency = max_frequency_hz
        self.max_temperature = max_temperature_c
        self.max_charge_density = max_charge_density_uc_cm2

    def evaluate(self, twin: DigitalTwin) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluates the current state against the safety envelope.
        Returns (is_safe, iso_14971_metrics).
        """
        # Current state
        amp = twin.stimulation_amplitude_ma
        freq = twin.stimulation_frequency_hz
        temp = twin.temperature_celsius
        
        # Simplistic charge density calculation: Amplitude (mA) * Pulse Width (ms) / Electrode Area (cm^2)
        # We assume standard 90us pulse width and 0.05 cm^2 electrode area for this simulation
        pulse_width_ms = 0.09
        area_cm2 = 0.05
        charge_density = (amp * pulse_width_ms) / area_cm2

        # Polynomial constraint surface: distance from the safe origin (0, 0, 37.0, 0)
        # Normalized by maximum allowable limits. If sum of squared normalized distances > 1.0, breach!
        norm_amp = amp / self.max_amplitude
        norm_freq = freq / self.max_frequency
        norm_temp = max(0, temp - 37.0) / (self.max_temperature - 37.0)
        norm_cd = charge_density / self.max_charge_density
        
        envelope_value = (norm_amp**2 + norm_freq**2 + norm_temp**2 + norm_cd**2)
        
        is_safe = True
        hazard_state = "NOMINAL"
        severity = "NEGLIGIBLE"
        action = "MONITOR"
        
        if envelope_value > 1.0 or temp > self.max_temperature or charge_density > self.max_charge_density:
            is_safe = False
            hazard_state = "ENVELOPE_BREACH"
            
            if temp > 40.0 or charge_density > 40.0:
                severity = "CATASTROPHIC"
                action = "EMERGENCY_SHUTDOWN"
            else:
                severity = "CRITICAL"
                action = "FALLBACK_SAFE_MODE"
                
        metrics = {
            "envelope_value": envelope_value,
            "charge_density": charge_density,
            "hazard_state": hazard_state,
            "iso_severity": severity,
            "clinical_action": action,
            "tissue_damage_risk": "HIGH" if not is_safe else "NONE"
        }
        
        return is_safe, metrics
