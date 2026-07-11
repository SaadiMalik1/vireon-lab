import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import os

from neuroshield.core.twin import DigitalTwin
from neuroshield.core.utils import calculate_rms
from neuroshield.core.event_bus import EventBus, Event
from neuroshield.core.threat_intel import ThreatIntelligence

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


def calculate_spectral_features(signal: np.ndarray) -> Tuple[float, float]:
    """
    Computes normalized spectral entropy and Spectral Crest Factor of a 1D signal.
    """
    n = len(signal)
    if n <= 1:
        return 1.0, 1.0
    fft_vals = np.fft.rfft(signal)
    psd = np.abs(fft_vals) ** 2
    psd_sum = np.sum(psd)
    if psd_sum == 0:
        return 0.0, 1.0
        
    psd_norm = psd / psd_sum
    psd_norm_nz = psd_norm[psd_norm > 0]
    entropy = -np.sum(psd_norm_nz * np.log2(psd_norm_nz))
    max_entropy = np.log2(len(psd))
    entropy_norm = float(entropy / max_entropy) if max_entropy > 0 else 1.0
    
    # Crest factor: peak power / average power
    peak_power = np.max(psd)
    avg_power = np.mean(psd)
    crest_factor = float(peak_power / avg_power) if avg_power > 0 else 1.0
    
    return entropy_norm, crest_factor


class LinearAutoencoderIDS:
    """
    A lightweight, numpy-based linear autoencoder (PCA) for anomaly detection.
    Detects structural deviations in signal covariance that evade basic RMS/Spectral checks.
    """
    def __init__(self, n_components: int = 2, learning_rate: float = 0.01):
        self.n_components = n_components
        self.lr = learning_rate
        self.components: Optional[np.ndarray] = None
        self.mean: Optional[np.ndarray] = None
        self.is_fitted = False
        self.reconstruction_errors: List[float] = []
        self.calibration_buffer = []

    def calibrate(self, data: np.ndarray):
        """Offline batch calibration to establish a mathematically stable baseline via Eigendecomposition."""
        obs = data.T
        self.mean = np.mean(obs, axis=0)
        obs_c = obs - self.mean
        cov = np.cov(obs_c, rowvar=False)
        # Using eigh for symmetric matrix
        vals, vecs = np.linalg.eigh(cov)
        # Top n_components
        self.components = vecs[:, -self.n_components:].T
        self.is_fitted = True

    def detect(self, data: np.ndarray) -> float:
        if not self.is_fitted:
            self.calibration_buffer.append(data)
            # Buffer initial data for batch calibration
            if len(self.calibration_buffer) >= 100:
                stacked_data = np.concatenate(self.calibration_buffer, axis=1)
                self.calibrate(stacked_data)
                self.calibration_buffer = []
            return 0.0
        
        # Frozen Inference Phase: No online SGD adaptation to anomalies
        obs = data.T
        x_c = obs - self.mean
        y = x_c @ self.components.T
        reconstruction = y @ self.components
        errors = np.mean((x_c - reconstruction)**2, axis=1)
        mean_error = float(np.mean(errors))
        
        self.reconstruction_errors.append(mean_error)
        if len(self.reconstruction_errors) > 100:
            self.reconstruction_errors.pop(0)
            
        return mean_error

class DeepAutoencoderIDS:
    """
    A PyTorch-based Deep Autoencoder for non-linear anomaly detection on EEG data.
    """
    def __init__(self, input_dim: int, hidden_dim: int = 4, learning_rate: float = 0.001):
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is not available.")
        
        self.model = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim)
        )
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.MSELoss()
        self.is_fitted = False
        self.reconstruction_errors: List[float] = []
        self.calibration_buffer = []

    def calibrate(self, data: np.ndarray):
        """Offline batch calibration phase with validation split and early stopping."""
        obs = torch.tensor(data.T, dtype=torch.float32)
        
        # 80/20 train/val split
        n_samples = obs.size(0)
        split_idx = int(0.8 * n_samples)
        
        train_data = obs[:split_idx]
        val_data = obs[split_idx:]
        
        best_val_loss = float('inf')
        patience = 5
        patience_counter = 0
        
        # Train for multiple epochs on the buffered baseline data
        for _ in range(50):
            self.model.train()
            self.optimizer.zero_grad()
            output = self.model(train_data)
            loss = self.criterion(output, train_data)
            loss.backward()
            self.optimizer.step()
            
            # Validation
            if split_idx < n_samples:
                self.model.eval()
                with torch.no_grad():
                    val_output = self.model(val_data)
                    val_loss = self.criterion(val_output, val_data).item()
                    
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    
                if patience_counter >= patience:
                    # Early stopping triggered
                    break
        self.is_fitted = True

    def detect(self, data: np.ndarray) -> float:
        if not self.is_fitted:
            self.calibration_buffer.append(data)
            # Buffer initial data for batch calibration
            if len(self.calibration_buffer) >= 100:
                stacked_data = np.concatenate(self.calibration_buffer, axis=1)
                self.calibrate(stacked_data)
                self.calibration_buffer = []
            return 0.0
            
        # Frozen Inference Phase: No online SGD adaptation to anomalies
        obs = torch.tensor(data.T, dtype=torch.float32)
        self.model.eval()
        with torch.no_grad():
            reconstruction = self.model(obs)
            errors = torch.mean((obs - reconstruction) ** 2, dim=1).numpy()
            
        mean_error = float(np.mean(errors))
        self.reconstruction_errors.append(mean_error)
        if len(self.reconstruction_errors) > 100:
            self.reconstruction_errors.pop(0)
            
        return mean_error


class CoherenceEngine:
    """
    Implements the QIF Coherence (Cs) metric for cross-modal validation.
    If a primary cortical stimulation occurs (e.g. visual phosphene), a corresponding
    autonomic response (e.g. pupil dilation) should follow. If missing, trust drops.
    """
    def __init__(self):
        self.baseline_pupil = 4.0
        self.coherence_score = 1.0

    def evaluate(self, primary_active: bool, secondary_val: float) -> float:
        if primary_active:
            if secondary_val < 4.2:
                # Spoofed signal! Stimulation is happening but body isn't reacting
                self.coherence_score = max(0.0, self.coherence_score - 0.2)
            else:
                self.coherence_score = min(1.0, self.coherence_score + 0.05)
        else:
            # Recovery to baseline
            self.coherence_score = min(1.0, self.coherence_score + 0.01)
            
        return self.coherence_score


class NeuroIDS:
    """
    Intrusion Detection System for Brain-Computer Interfaces.
    Monitors signal dynamics and clinical trends in real time to detect
    spoofing, jamming, and loop synchronization attacks.
    """

    def __init__(self, twin: DigitalTwin, event_bus: Optional[EventBus] = None,
                 rms_high_threshold: float = 120.0,
                 rms_low_threshold: float = 0.5,
                 beta_power_threshold: float = 35.0):
        self.twin = twin
        self.event_bus = event_bus

        # Configurable detection thresholds
        self.rms_high_threshold = rms_high_threshold
        self.rms_low_threshold = rms_low_threshold
        self.beta_power_threshold = beta_power_threshold

        self.history_beta_power: List[float] = []
        self.command_history: List[Tuple[float, float, float]] = []
        
        # Dynamic Baseline and Drift Detection State
        self.dynamic_baseline_enabled = True
        self.ewma_alpha = 0.05
        self.rms_ewma: Dict[int, float] = {}
        self.rms_var: Dict[int, float] = {}
        
        # CUSUM parameters for 'low and slow' drift attacks
        self.cusum_k = 0.5   # Slack parameter
        self.cusum_h = 5.0   # Alarm threshold
        self.cusum_pos: Dict[int, float] = {}
        self.cusum_neg: Dict[int, float] = {}
        
        if TORCH_AVAILABLE:
            self.autoencoder = DeepAutoencoderIDS(input_dim=self.twin.num_channels)
        else:
            self.autoencoder = LinearAutoencoderIDS()
            
        self.ae_threshold = 0.5
        self.coherence_engine = CoherenceEngine()
        
        # Initialize Threat Intelligence for logging
        registry_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../neurosecurity/datalake/qtara-registrar.json'))
        self.threat_intel = ThreatIntelligence(registry_path)

        # Detection logs
        self.detections: List[Dict[str, Any]] = []
    def analyze_signal(self, data: np.ndarray) -> List[str]:
        anomalies = []
        n_channels = data.shape[0]

        for ch in range(n_channels):
            ch_signal = data[ch, :]
            rms = calculate_rms(ch_signal)

            # Initialize EWMA baseline if needed
            if self.dynamic_baseline_enabled and ch not in self.rms_ewma:
                # If the first packet is already anomalously high, we shouldn't trust it as baseline
                if rms < self.rms_high_threshold:
                    self.rms_ewma[ch] = rms
                else:
                    self.rms_ewma[ch] = self.rms_high_threshold / 2.0  # Safe nominal default
                self.rms_var[ch] = 1.0
                self.cusum_pos[ch] = 0.0
                self.cusum_neg[ch] = 0.0

            # 1. Detect extreme noise injections (jamming/saturation)
            # Check static absolute bounds first
            if rms > self.rms_high_threshold:
                anomalies.append("HIGH_NOISE_ANOMALY")
                self._log_detection("HIGH_NOISE_ANOMALY", ch, rms)
            # Check dynamic 3-sigma statistical bound
            elif self.dynamic_baseline_enabled and ch in self.rms_ewma:
                std_dev = np.sqrt(self.rms_var[ch]) if self.rms_var[ch] > 0 else 1.0
                if rms > self.rms_ewma[ch] + 3.0 * std_dev and rms > self.rms_low_threshold * 2:
                    anomalies.append("HIGH_NOISE_ANOMALY")
                    self._log_detection("HIGH_NOISE_ANOMALY", ch, rms)

            # 2. Detect signal suppression (attenuation/grounding attacks)
            if rms < self.rms_low_threshold:
                anomalies.append("SIGNAL_SUPPRESSION_ANOMALY")
                self._log_detection("SIGNAL_SUPPRESSION_ANOMALY", ch, rms)
                
            # 2b. Dynamic Baseline & CUSUM slow-drift detection update
            if self.dynamic_baseline_enabled and ch in self.rms_ewma:
                diff = rms - self.rms_ewma[ch]
                self.rms_ewma[ch] += self.ewma_alpha * diff
                self.rms_var[ch] = (1 - self.ewma_alpha) * (self.rms_var[ch] + self.ewma_alpha * diff**2)
                
                std_dev = np.sqrt(self.rms_var[ch]) if self.rms_var[ch] > 0 else 1.0
                z_score = diff / std_dev
                
                self.cusum_pos[ch] = max(0.0, self.cusum_pos[ch] + z_score - self.cusum_k)
                self.cusum_neg[ch] = max(0.0, self.cusum_neg[ch] - z_score - self.cusum_k)
                
                if self.cusum_pos[ch] > self.cusum_h or self.cusum_neg[ch] > self.cusum_h:
                    anomalies.append("SLOW_DRIFT_ANOMALY")
                    self._log_detection("SLOW_DRIFT_ANOMALY", ch, rms)
                    # Reset to avoid alarm fatigue
                    self.cusum_pos[ch] = 0.0
                    self.cusum_neg[ch] = 0.0
            
            # 3. Detect spoofing via spectral entropy and Crest Factor (defeats noise padding)
            entropy, crest_factor = calculate_spectral_features(ch_signal)
            if entropy < 0.20 or crest_factor > 15.0:
                anomalies.append("SPECTRAL_SPOOFING_ANOMALY")
                self._log_detection("SPECTRAL_SPOOFING_ANOMALY", ch, crest_factor)

        # 4. Detect structural deviations using autoencoder
        ae_error = self.autoencoder.detect(data)
        if ae_error > self.ae_threshold:
            anomalies.append("STRUCTURAL_DEVIATION_ANOMALY")
            self._log_detection("STRUCTURAL_DEVIATION_ANOMALY", -1, ae_error)

        # 5. QIF Cross-Modal Coherence (Cs) Check
        # If stimulation is running, the twin's secondary markers must match
        is_stimulating = self.twin.stimulation_enabled and self.twin.stimulation_amplitude_ma > 0
        cs_score = self.coherence_engine.evaluate(is_stimulating, self.twin.autonomic_pupil_dilation_mm)
        
        if cs_score < 0.5:
            anomalies.append("COHERENCE_FAILURE_ANOMALY")
            self._log_detection("COHERENCE_FAILURE_ANOMALY", -1, cs_score)

        unique_anomalies = list(set(anomalies))
        if unique_anomalies and self.event_bus:
            self.event_bus.publish(Event(
                topic="ids.anomaly_detected",
                data={
                    "anomalies": unique_anomalies,
                    "sim_clock": self.twin.get_sim_clock()
                },
                source="ids"
            ))

        return unique_anomalies

    def analyze_commands(self, amplitude: float, frequency: float) -> List[str]:
        """
        IDS behavioral analysis to detect high-frequency parameter manipulation (jitter attacks).
        """
        anomalies = []
        current_time = self.twin.get_sim_clock()
        self.command_history.append((current_time, amplitude, frequency))
        self.command_history = [x for x in self.command_history if current_time - x[0] <= 3.0]

        # Count parameter changes within the 3-second window
        changes = 0
        if len(self.command_history) > 1:
            for i in range(1, len(self.command_history)):
                if self.command_history[i][1] != self.command_history[i-1][1] or self.command_history[i][2] != self.command_history[i-1][2]:
                    changes += 1

        if changes >= 5:
            anomalies.append("HIGH_FREQUENCY_COMMAND_ANOMALY")
            self._log_detection("HIGH_FREQUENCY_COMMAND_ANOMALY", -1, float(changes))

            if self.event_bus:
                self.event_bus.publish(Event(
                    topic="ids.command_jitter_detected",
                    data={
                        "changes_count": changes,
                        "sim_clock": current_time
                    },
                    source="ids"
                ))
        return anomalies

    def analyze_clinical(self, current_beta_power: float, stim_enabled: bool, amplitude: float) -> List[str]:
        anomalies = []
        self.history_beta_power.append(current_beta_power)
        if len(self.history_beta_power) > 20:
            self.history_beta_power.pop(0)

        # 3. Detect Pathological Synchronization (Phase-Shifting attack)
        # If stimulation is active (>1.0mA) and beta power continues to rise or remains high
        # (e.g. mean power > beta_power_threshold uV^2 over last 5 steps), we have synchronization!
        if stim_enabled and amplitude > 1.0 and len(self.history_beta_power) >= 5:
            recent_mean = np.mean(self.history_beta_power[-5:])
            if recent_mean > self.beta_power_threshold:
                anomalies.append("PATHOLOGICAL_SYNCHRONIZATION_ATTACK")
                self._log_detection("PATHOLOGICAL_SYNCHRONIZATION_ATTACK", -1, recent_mean)

        if anomalies and self.event_bus:
            self.event_bus.publish(Event(
                topic="ids.clinical_anomaly_detected",
                data={
                    "anomalies": anomalies,
                    "sim_clock": self.twin.get_sim_clock()
                },
                source="ids"
            ))

        return anomalies

    def _log_detection(self, anomaly_type: str, channel: int, value: float):
        tara_id = None
        mitre_id = None
        severity = "Medium"
        description = anomaly_type
        
        # Heuristic mapping for basic anomalies
        if anomaly_type == "HIGH_NOISE_ANOMALY":
            tara_id = "QIF-T2102"
        elif anomaly_type == "COHERENCE_FAILURE_ANOMALY":
            tara_id = "QIF-T2201"
        elif anomaly_type == "PATHOLOGICAL_SYNCHRONIZATION_ATTACK":
            tara_id = "QIF-T2301"
        elif anomaly_type == "SPECTRAL_SPOOFING_ANOMALY":
            tara_id = "QIF-T2202"
        elif anomaly_type == "SIGNAL_SUPPRESSION_ANOMALY":
            tara_id = "QIF-T2101"
            
        if tara_id and hasattr(self.threat_intel, "loader") and self.threat_intel.loader:
            tech = self.threat_intel.loader.get_technique(tara_id)
            if tech:
                if tech.mitre and tech.mitre.tactics:
                    mitre_id = tech.mitre.tactics[0]
                severity = tech.severity
                description = tech.name
            
        # Brain Region Mapping
        brain_region_id = None
        brain_region_name = None
        # Simple heuristic mapping for now, assuming front channels are PFC and back are V1/PPC
        if channel in [0, 1]:
            brain_region_id = "pfc"
        elif channel in [2, 3]:
            brain_region_id = "m1"
        elif channel in [4, 5]:
            brain_region_id = "ppc"
        else:
            brain_region_id = "v1"
            
        if self.twin and hasattr(self.twin, "brain_regions") and brain_region_id in self.twin.brain_regions:
            brain_region_name = self.twin.brain_regions[brain_region_id].get("name")
            
        log_entry = {
            "timestamp": self.twin.get_sim_clock(),
            "anomaly_type": anomaly_type,
            "channel": channel,
            "value": round(value, 2),
            "confidence": 0.95 if anomaly_type != "PATHOLOGICAL_SYNCHRONIZATION_ATTACK" else 0.85,
            "tara_id": tara_id,
            "mitre_id": mitre_id,
            "severity": severity,
            "description": description,
            "brain_region_id": brain_region_id,
            "brain_region_name": brain_region_name
        }
        self.detections.append(log_entry)
        if len(self.detections) > 1000:
            self.detections.pop(0)
        
        # Print for visibility
        print(f"[NeuroIDS] Detection: {anomaly_type} on Ch{channel} (Region: {brain_region_name}) -> TARA: {tara_id} ({description}) | Severity: {severity}")


class NeuroIPS:
    """
    Intrusion Prevention System for Brain-Computer Interfaces.
    Executes automated mitigation actions: clamps stimulation parameters to safe thresholds,
    filters corrupted signals, and enforces link layer security.
    """

    def __init__(self, twin: DigitalTwin, ids: NeuroIDS, event_bus: Optional[EventBus] = None,
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

    def sanitize_stimulation_write(self, amplitude: float, frequency: float) -> Tuple[float, float]:
        """
        Sanitizes raw stimulator write commands to protect patient tissue.
        Prevents dangerous high-current command injections and cumulative charge buildup.
        """
        import math
        if math.isnan(amplitude) or math.isinf(amplitude):
            amplitude = 0.0
        if math.isnan(frequency) or math.isinf(frequency):
            frequency = 0.0
            
        current_time = self.twin.get_sim_clock()
        
        # Check command behavioral rate limit
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
            # Revert to last stable stimulation settings
            if len(self.stim_history) > 0:
                return self.stim_history[-1][1], self.stim_history[-1][2]
            return 0.0, 0.0

        # Calculate Leaky Integrator Thermal Dose (Pennes Bioheat Equation approximation)
        dt = 0.0
        power_injected = 0.0
        if len(self.stim_history) > 0:
            dt = current_time - self.stim_history[-1][0]
            last_amp = self.stim_history[-1][1]
            last_freq = self.stim_history[-1][2]
            # Power injected by the PREVIOUS pulse over the interval dt
            power_injected = abs(last_amp) * abs(last_freq)

        self.stim_history.append((current_time, amplitude, frequency))
        # Keep recent history for coherence checks, though leaky integrator doesn't strictly need it all
        self.stim_history = [x for x in self.stim_history if current_time - x[0] <= 10.0]

        if dt > 0:
            # Dissipation factor (tau = 60 seconds thermal relaxation time)
            tau_dissipation = 60.0
            decay_factor = np.exp(-dt / tau_dissipation)

            # Update Leaky Integrator
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
            return 0.0, 0.0  # Force shutoff to protect tissue

        # Thermodynamic temperature protection (Pulsed-load / Evasion mitigation)
        if self.twin.temperature_celsius >= 40.5:
            self.blocked_attacks_count += 1
            self.clamping_active = True
            self.twin.set_clinical_alert(True, "IPS: Thermal Tissue Hazard Detected")
            self.twin.update_clinical_risk(
                hazard_state="TISSUE_HEATING",
                iso_severity="CRITICAL",
                tissue_damage_risk="HIGH",
                clinical_action="SHUTDOWN"
            )
            return 0.0, 0.0

        # Patient State Coherence Model (Paradox 3 solution)
        coherence_clamped = False
        if len(self.stim_history) > 1:
            last_amp = self.stim_history[-2][1]
            
            # 1. Delta rate limit (Max change of 0.5 mA per write)
            if abs(amplitude - last_amp) > 0.5:
                amplitude = last_amp + np.sign(amplitude - last_amp) * 0.5
                self.clamping_active = True
                coherence_clamped = True
                self.blocked_attacks_count += 1
                self.twin.set_clinical_alert(True, "IPS Clamped: Coherence Delta Rate Limit")
                self.stim_history[-1] = (current_time, amplitude, frequency)
                
            # 2. Clinical state coherence (Cannot increase stimulation if beta power is low, OR if IDS anomalies are active)
            if len(self.ids.history_beta_power) > 0:
                last_beta = self.ids.history_beta_power[-1]
                # Cross-reference with active anomalies to prevent beta inflation evasion
                active_anomalies = self.ids.detections[-5:] # check recent detections
                has_active_anomaly = any(d["timestamp"] >= current_time - 3.0 for d in active_anomalies)
                
                if (last_beta < 15.0 or has_active_anomaly) and amplitude > last_amp:
                    amplitude = last_amp
                    self.clamping_active = True
                    coherence_clamped = True
                    self.blocked_attacks_count += 1
                    msg = "IPS Clamped: Coherence State Untrusted (Anomaly Active)" if has_active_anomaly else "IPS Clamped: Coherence State Check Failed"
                    self.twin.set_clinical_alert(True, msg)
                    self.stim_history[-1] = (current_time, amplitude, frequency)

        if coherence_clamped:
            return amplitude, frequency

        # Hard limit ceiling check
        if amplitude > self.max_stimulation_amplitude_ma:
            self.blocked_attacks_count += 1
            self.clamping_active = True

            # Log command blocking directly into Digital Twin history
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
        """
        Active channel filtering and reconstruction.
        Mutes anomalous channels and fills with baseline noise to keep decoder stable.
        """
        clean_data = data.copy()
        muted_channels = []

        if "HIGH_NOISE_ANOMALY" in anomalies or "SIGNAL_SUPPRESSION_ANOMALY" in anomalies:
            # Filter and replace abnormal channels with low-amplitude nominal noise
            for ch in range(clean_data.shape[0]):
                ch_signal = clean_data[ch, :]
                rms = calculate_rms(ch_signal)
                if rms > self.ids.rms_high_threshold or rms < self.ids.rms_low_threshold:
                    clean_data[ch, :] = np.random.normal(0, 2.0, clean_data.shape[1])
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

    def check_rf_environment(self):
        drop_rate = getattr(self.twin, "rf_packet_drop_rate", 0.0)
        # If dropping more than 30% of packets, trigger RF Jamming Alert
        if drop_rate >= 0.3:
            self.jamming_alerts += 1
            self.twin.set_clinical_alert(True, f"BLE Link Guard: Severe RF Jamming Detected ({drop_rate*100:.0f}% drops)")
            if self.event_bus:
                self.event_bus.publish(Event(
                    topic="link_guard.jamming_detected",
                    data={"drop_rate": drop_rate, "sim_clock": self.twin.get_sim_clock()},
                    source="link_guard"
                ))

    def verify_mtu(self, requested_mtu: int) -> int:
        # BLE specification minimum MTU size is 23 bytes
        if requested_mtu < 23:
            self.blocked_mtu_abuses += 1
            self.twin.set_clinical_alert(True, "BLE Link Guard: Blocked MTU Abuse")

            if self.event_bus:
                self.event_bus.publish(Event(
                    topic="link_guard.mtu_abuse_blocked",
                    data={
                        "requested_mtu": requested_mtu,
                        "enforced_mtu": 23,
                        "sim_clock": self.twin.get_sim_clock()
                    },
                    source="link_guard"
                ))

            return 23  # Enforce spec minimum
        return requested_mtu
