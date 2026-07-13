import numpy as np
from vireon.core.twin import DigitalTwin

def calculate_rms(signal: np.ndarray) -> float:
    """Calculates the Root Mean Square (RMS) of a 1D signal."""
    if len(signal) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(signal))))

def calculate_bandpower(signal: np.ndarray, sample_rate: int, band: tuple[float, float]) -> float:
    """
    Calculates the average power in a specific frequency band using FFT.
    Uses numpy FFT to avoid dependency on scipy.signal.
    """
    n = len(signal)
    if n == 0:
        return 0.0
    
    # Compute real FFT
    fft_vals = np.fft.rfft(signal)
    fft_freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
    
    # Power spectral density estimate
    psd = (np.abs(fft_vals) ** 2) / (sample_rate * n)
    
    # Find indices corresponding to the frequency band
    idx = (fft_freqs >= band[0]) & (fft_freqs <= band[1])
    if not np.any(idx):
        return 0.0
        
    return float(np.mean(psd[idx]))

def format_telemetry_table(twin: DigitalTwin) -> str:
    """Formats the current digital twin state as an ASCII table."""
    state = twin.get_state()
    
    lines = []
    lines.append("=" * 60)
    lines.append(f" NEUROSHIELD TELEMETRY - {state['device_id'].upper()}")
    lines.append("=" * 60)
    lines.append(f" Connection Status : {'CONNECTED' if state['connected'] else 'DISCONNECTED':<12} | Battery Level : {state['battery_level']}%")
    lines.append(f" Firmware Version  : {state['firmware_version']:<12} | Sample Rate   : {state['sample_rate']} Hz")
    lines.append("-" * 60)
    
    # Electrode Impedances
    imp_strs = []
    for ch, val in sorted(state['electrode_impedances'].items(), key=lambda x: int(x[0])):
        imp_strs.append(f"Ch{ch}: {val}kΩ")
    
    # Group impedances into 4 per line
    for i in range(0, len(imp_strs), 4):
        lines.append(" " + " | ".join(imp_strs[i:i+4]))
        
    lines.append("-" * 60)
    lines.append(f" Clinical Status   : {state['clinical_status']:<12} | Alert Active  : {str(state['clinical_alert_active']).upper()}")
    lines.append(f" Dec. Confidence   : {state['decoder_confidence']:.2f}         | Therapy State : {'ACTIVE' if state['stimulation_enabled'] else 'SUSPENDED'}")
    if state['stimulation_enabled']:
        lines.append(f" Stimulation Params: {state['stimulation_amplitude_ma']} mA @ {state['stimulation_frequency_hz']} Hz")
    lines.append("-" * 60)
    lines.append(f" Hazard State (ISO): {state.get('hazard_state', 'NOMINAL'):<12} | Severity      : {state.get('iso_severity', 'NEGLIGIBLE')}")
    lines.append(f" Tissue Damage Risk: {state.get('tissue_damage_risk', 'NONE'):<12} | Risk Action   : {state.get('clinical_action', 'MONITOR')}")
    lines.append("=" * 60)
    
    return "\n".join(lines)
