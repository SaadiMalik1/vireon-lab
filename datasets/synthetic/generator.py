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

"""
Synthetic Validation Generator

Generates labeled synthetic traces (EEG/Telemetry) to validate
the VIREON anomaly detection and ZTA components.
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
    base_dir = Path(__file__).parent
    
    out_dir = base_dir / "normal"
    out_dir.mkdir(exist_ok=True, parents=True)
    
    attack_dir = base_dir / "attacks" / "held_out"
    attack_dir.mkdir(exist_ok=True, parents=True)

    # 1. Clean Baseline (30 seconds for better calibration)
    clean = generate_clean_trace(30.0)
    with open(out_dir / "clean_baseline.json", "w") as f:
        json.dump({"fs": 250, "data": clean, "label": "normal"}, f)
        
    # Generate multiple test points for attacks to allow stable ROC
    for i in range(5):
        # Noise Attack
        noisy = inject_noise_attack(clean, 5 * 250, 7 * 250)
        with open(attack_dir / f"noise_attack_{i}.json", "w") as f:
            json.dump({"fs": 250, "data": noisy, "label": "attack", "attack_type": "noise"}, f)
            
        # Packet Loss Attack
        flatline = inject_packet_loss(clean, 4 * 250, 9 * 250)
        with open(attack_dir / f"packet_loss_{i}.json", "w") as f:
            json.dump({"fs": 250, "data": flatline, "label": "attack", "attack_type": "packet_loss"}, f)

    print("[+] Generated synthetic validation corpus (held_out attacks).")

if __name__ == "__main__":
    generate_synthetic_corpus()
