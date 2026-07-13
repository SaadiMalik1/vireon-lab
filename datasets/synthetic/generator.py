"""
Synthetic Validation Generator

Generates labeled synthetic traces (EEG/Telemetry) to validate
the NeuroShield anomaly detection and ZTA components.
"""
import math
import random
import json
from pathlib import Path

def generate_clean_trace(duration_sec: float = 10.0, fs: int = 250) -> list:
    """Generates a clean synthetic EEG trace (1 channel)."""
    samples = []
    total_samples = int(duration_sec * fs)
    for i in range(total_samples):
        t = i / fs
        # Synthetic alpha + beta + slow drift
        val = (
            math.sin(2 * math.pi * 10 * t) * 0.5 + 
            math.sin(2 * math.pi * 20 * t) * 0.2 +
            math.sin(2 * math.pi * 0.5 * t) * 0.8
        )
        samples.append(val)
    return samples

def inject_noise_attack(trace: list, start_idx: int, end_idx: int) -> list:
    """Injects high-frequency adversarial noise into a trace."""
    modified = trace.copy()
    for i in range(start_idx, min(end_idx, len(modified))):
        modified[i] += (random.random() * 2.0) - 1.0  # High amplitude random noise
    return modified

def inject_packet_loss(trace: list, start_idx: int, end_idx: int) -> list:
    """Simulates BLE MTU DoS leading to telemetry packet loss (flatlining)."""
    modified = trace.copy()
    for i in range(start_idx, min(end_idx, len(modified))):
        modified[i] = 0.0
    return modified

def generate_synthetic_corpus():
    """Generates the base synthetic datasets and saves them to disk."""
    out_dir = Path(__file__).parent / "normal"
    out_dir.mkdir(exist_ok=True)
    
    attack_dir = Path(__file__).parent / "attacks"
    attack_dir.mkdir(exist_ok=True)

    # 1. Clean Baseline (10 seconds)
    clean = generate_clean_trace(10.0)
    with open(out_dir / "clean_baseline.json", "w") as f:
        json.dump({"fs": 250, "data": clean, "label": "normal"}, f)
        
    # 2. Noise Attack (t=5s to t=7s)
    noisy = inject_noise_attack(clean, 5 * 250, 7 * 250)
    with open(attack_dir / "noise_attack.json", "w") as f:
        json.dump({"fs": 250, "data": noisy, "label": "attack", "attack_type": "noise"}, f)
        
    # 3. Packet Loss Attack (t=4s to t=9s)
    flatline = inject_packet_loss(clean, 4 * 250, 9 * 250)
    with open(attack_dir / "packet_loss.json", "w") as f:
        json.dump({"fs": 250, "data": flatline, "label": "attack", "attack_type": "packet_loss"}, f)

    print("[+] Generated synthetic validation corpus.")

if __name__ == "__main__":
    generate_synthetic_corpus()
