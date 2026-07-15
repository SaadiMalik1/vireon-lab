import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import os
import logging
import threading
import importlib.resources as pkg_resources

from vireon.core.twin import DigitalTwin
from vireon.core.event_bus import EventBus, Event
from vireon.core.threat_intel import ThreatIntelligence
from vireon.core.utils import calculate_rms

logger = logging.getLogger(__name__)

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
        self.calibration_buffer: list[np.ndarray] = []

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

if TORCH_AVAILABLE:
    class LSTMAutoencoderModel(nn.Module):
        def __init__(self, input_dim: int, hidden_dim: int = 8):
            super().__init__()
            self.encoder = nn.LSTM(input_size=input_dim, hidden_size=hidden_dim, num_layers=1, batch_first=True)
            self.decoder = nn.LSTM(input_size=hidden_dim, hidden_size=input_dim, num_layers=1, batch_first=True)
            
        def forward(self, x):
            # x shape: (batch_size, sequence_length, input_dim)
            encoded, _ = self.encoder(x)
            decoded, _ = self.decoder(encoded)
            return decoded
else:
    class LSTMAutoencoderModel:  # type: ignore[no-redef]
        pass

class DeepAutoencoderIDS:
    """
    A PyTorch-based LSTM Deep Autoencoder for non-linear temporal anomaly detection on EEG data.
    """
    def __init__(self, input_dim: int, hidden_dim: int = 8, learning_rate: float = 0.001):
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is not available.")
        
        self.model = LSTMAutoencoderModel(input_dim, hidden_dim)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.MSELoss()
        self.is_fitted = False
        self.reconstruction_errors: List[float] = []
        self.calibration_buffer: list[np.ndarray] = []

    def calibrate(self, data: np.ndarray):
        """Offline batch calibration phase with validation split and early stopping."""
        # data is (channels, samples). We transpose to (samples, channels)
        # For LSTM, we reshape to (1, seq_length, input_dim)
        obs = torch.tensor(data.T, dtype=torch.float32).unsqueeze(0)
        
        # Split sequence into train/val (not straightforward for 1 sequence, so we split across time)
        seq_len = obs.size(1)
        split_idx = int(0.8 * seq_len)
        
        train_data = obs[:, :split_idx, :]
        val_data = obs[:, split_idx:, :]
        
        best_val_loss = float('inf')
        patience = 5
        patience_counter = 0
        
        # Train for multiple epochs on the buffered baseline data
        for _ in range(100):
            self.model.train()
            self.optimizer.zero_grad()
            output = self.model(train_data)
            loss = self.criterion(output, train_data)
            loss.backward()
            self.optimizer.step()
            
            # Validation
            if split_idx < seq_len:
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
            if len(self.calibration_buffer) >= 50:
                stacked_data = np.concatenate(self.calibration_buffer, axis=1)
                self.calibrate(stacked_data)
                self.calibration_buffer = []
            return 0.0
            
        # Frozen Inference Phase
        obs = torch.tensor(data.T, dtype=torch.float32).unsqueeze(0)
        self.model.eval()
        with torch.no_grad():
            reconstruction = self.model(obs)
            # calculate MSE across feature dimension, then mean over sequence
            errors = torch.mean((obs - reconstruction) ** 2, dim=2).squeeze(0).numpy()
            
        mean_error = float(np.mean(errors))
        self.reconstruction_errors.append(mean_error)
        if len(self.reconstruction_errors) > 100:
            self.reconstruction_errors.pop(0)
            
        return mean_error


class CoherenceEngine:
    """
    Implements the Cross-Modal Coherence metric for validation.
    If a primary cortical stimulation occurs (e.g. visual phosphene), a corresponding
    autonomic response (e.g. pupil dilation) should follow. If missing, trust drops.
    """
    def __init__(self):
        self.baseline_pupil = 4.0
        self.coherence_score = 1.0
        self.primary_history = []

    def evaluate(self, primary_active: bool, secondary_val: float) -> float:
        self.primary_history.append(primary_active)
        if len(self.primary_history) > 10:  # ~200-500ms lag window depending on tick rate
            self.primary_history.pop(0)
            
        recently_active = any(self.primary_history)
        
        if recently_active:
            if secondary_val < 4.2:
                # Spoofed signal! Stimulation is happening but body isn't reacting
                self.coherence_score = max(0.0, self.coherence_score - 0.2)
            else:
                self.coherence_score = min(1.0, self.coherence_score + 0.05)
        else:
            # Recovery to baseline
            self.coherence_score = min(1.0, self.coherence_score + 0.01)
            
        return self.coherence_score


class SecurityEngine:
    """
    Intrusion Detection System for Brain-Computer Interfaces.
    Monitors signal dynamics and clinical trends in real time to detect
    spoofing, jamming, and loop synchronization attacks.
    """

    def __init__(self, twin: DigitalTwin, event_bus: Optional[EventBus] = None,
                 rms_high_threshold: float = 120.0,
                 rms_low_threshold: float = 0.5,
                 beta_power_threshold: float = 35.0,
                 seed: Optional[int] = None):
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
        
        self.autoencoder: Optional[DeepAutoencoderIDS] = None
        if TORCH_AVAILABLE:
            if seed is not None:
                torch.manual_seed(seed)
            self.autoencoder = DeepAutoencoderIDS(input_dim=self.twin.num_channels)
        else:
            self.autoencoder = None
        self.ae_threshold = 0.5
        self.coherence_engine = CoherenceEngine()
        
        self.history_confidence: List[float] = []
        # Initialize Threat Intelligence for logging
        try:
            registry_path = str(pkg_resources.files("vireon.plugins.clinical.data").joinpath("tara_stix.json"))
        except (AttributeError, ImportError):
            # Fallback for older python or missing package
            registry_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../plugins/clinical/data/tara_stix.json'))
        
        self.threat_intel = ThreatIntelligence(registry_path)
        self._lock = threading.RLock()

        # Detection logs
        self.detections: List[Dict[str, Any]] = []
    def score_signal(self, data: np.ndarray) -> float:
        """
        Returns a continuous anomaly score for use in threshold-swept ROC validation.
        Higher score = more anomalous.
        """
        scores = []
        n_channels = data.shape[0]
        
        # Explicit sanitization check
        if np.isnan(data).any():
            return float('inf')
            
        # 1. Structural Deviation (Autoencoder MSE)
        if self.autoencoder and getattr(self.autoencoder, 'is_fitted', False):
            # Evaluate without updating calibration buffer
            if TORCH_AVAILABLE and isinstance(self.autoencoder, DeepAutoencoderIDS):
                import torch
                obs = torch.tensor(data.T, dtype=torch.float32).unsqueeze(0)
                self.autoencoder.model.eval()
                with torch.no_grad():
                    reconstruction = self.autoencoder.model(obs)
                    errors = torch.mean((obs - reconstruction) ** 2, dim=2).squeeze(0).numpy()
                ae_error = float(np.mean(errors))
                scores.append(ae_error)
            elif isinstance(self.autoencoder, LinearAutoencoderIDS):
                obs = data.T
                x_c = obs - self.autoencoder.mean
                y = x_c @ self.autoencoder.components.T
                reconstruction = y @ self.autoencoder.components
                errors = np.mean((x_c - reconstruction)**2, axis=1)
                scores.append(float(np.mean(errors)))

        for ch in range(n_channels):
            ch_signal = data[ch, :]
            rms = calculate_rms(ch_signal)
            
            # 2. Dynamic Baseline Z-score
            if self.dynamic_baseline_enabled and ch in self.rms_ewma:
                std_dev = np.sqrt(self.rms_var[ch]) if self.rms_var[ch] > 0 else 1.0
                z_score = abs(rms - self.rms_ewma[ch]) / std_dev
                scores.append(z_score / 3.0)  # Normalize so 3-sigma is 1.0
                
            # 3. Spectral Spoofing
            entropy, crest_factor = calculate_spectral_features(ch_signal)
            if crest_factor > 1.0:
                scores.append(crest_factor / 15.0)
                
        return float(np.max(scores)) if scores else 0.0

    def analyze_signal(self, data: np.ndarray) -> List[str]:
        with self._lock:
            return self._analyze_signal(data)

    def _analyze_signal(self, data: np.ndarray) -> List[str]:
        anomalies = []
        n_channels = data.shape[0]

        # Explicit sanitization check (NaN Propagation Bypass mitigation)
        if np.isnan(data).any():
            anomalies.append("DATA_CORRUPTION_ANOMALY")
            self._log_detection("DATA_CORRUPTION_ANOMALY", -1, float('nan'))
            return anomalies

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
        if self.autoencoder:
            ae_error = self.autoencoder.detect(data)
            if ae_error > self.ae_threshold:
                anomalies.append("STRUCTURAL_DEVIATION_ANOMALY")
                self._log_detection("STRUCTURAL_DEVIATION_ANOMALY", -1, ae_error)

        # 5. Cross-Modal Coherence Check
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
        with self._lock:
            return self._analyze_commands(amplitude, frequency)

    def _analyze_commands(self, amplitude: float, frequency: float) -> List[str]:
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
        with self._lock:
            return self._analyze_clinical(current_beta_power, stim_enabled, amplitude)

    def _analyze_clinical(self, current_beta_power: float, stim_enabled: bool, amplitude: float) -> List[str]:
        anomalies = []
        self.history_beta_power.append(current_beta_power)
        if len(self.history_beta_power) > 1000:
            self.history_beta_power.pop(0)

        # 3. Detect Pathological Synchronization (Phase-Shifting attack)
        # If stimulation is active (>1.0mA) and beta power continues to rise or remains high
        # (e.g. mean power > beta_power_threshold uV^2 over last 5 steps), we have synchronization!
        if stim_enabled and amplitude > 1.0 and len(self.history_beta_power) >= 5:
            recent_mean = np.mean(self.history_beta_power[-5:])
            if recent_mean > self.beta_power_threshold:
                anomalies.append("PATHOLOGICAL_SYNCHRONIZATION_ATTACK")
                self._log_detection("PATHOLOGICAL_SYNCHRONIZATION_ATTACK", -1, float(recent_mean))

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
            tara_id = "CWE-284"
        elif anomaly_type == "BandPowerSkew":
            tara_id = "CWE-284"
        elif anomaly_type == "PathologicalSync":
            tara_id = "CWE-284"
        elif anomaly_type == "CoherenceDrop":
            tara_id = "CWE-400"
        elif anomaly_type == "Clipping/Saturation":
            tara_id = "CWE-400"
            
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
        
        # Log for visibility instead of print
        logger.warning(f"[NSAE] Detection: {anomaly_type} on Ch{channel} (Region: {brain_region_name}) -> CWE/Mapping: {tara_id} ({description}) | Severity: {severity}")


