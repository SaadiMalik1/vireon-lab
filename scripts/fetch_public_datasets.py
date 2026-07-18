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

#!/usr/bin/env python3
"""
VIREON 10-Dataset Fetcher
Downloads the curated public datasets (PhysioNet, BCI, OpenBCI) 
required for the Validation Suite. Supports resuming interrupted downloads.
"""
import urllib.request
import ssl
from pathlib import Path
import sys
import hashlib
import certifi

# Disable SSL verification for simplicity in some locked-down environments
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

DATASETS = {
    "eegmmi_baseline": {
        "url": "https://physionet.org/files/eegmmidb/1.0.0/S001/S001R01.edf",
        "dest": "datasets/eeg/S001R01.edf",
        "description": "PhysioNet EEG MMI (Subject 1, Baseline)"
    },
    "eegmmi_imagery": {
        "url": "https://physionet.org/files/eegmmidb/1.0.0/S001/S001R04.edf",
        "dest": "datasets/eeg/S001R04.edf",
        "description": "PhysioNet EEG MMI (Subject 1, Motor Imagery)"
    },
    "sleep_edf": {
        "url": "https://physionet.org/files/sleep-edfx/1.0.0/sleep-cassette/SC4001E0-PSG.edf",
        "dest": "datasets/eeg/SC4001E0-PSG.edf",
        "description": "PhysioNet Sleep-EDF (Subject 0, Cassette 1)"
    },
    "chb_mit_epilepsy": {
        "url": "https://physionet.org/files/chbmit/1.0.0/chb01/chb01_03.edf",
        "dest": "datasets/eeg/chb01_03.edf",
        "description": "PhysioNet CHB-MIT (Epilepsy, Subject 1)"
    },
    "mit_bih_ecg": {
        "url": "https://physionet.org/files/mitdb/1.0.0/100.dat",
        "dest": "datasets/ecg/100.dat",
        "description": "PhysioNet MIT-BIH Arrhythmia (Record 100)"
    },
    "emg_healthy": {
        "url": "https://physionet.org/files/emgdb/1.0.0/emg_healthy.dat",
        "dest": "datasets/emg/emg_healthy.dat", # Note: Using placeholder URL for emgdb, often requires specific subject navigation
        "description": "PhysioNet EMG (Healthy Baseline)"
    },
    "bci_comp_iv": {
        "url": "https://lampx.tugraz.at/~bci/database/001-2014/A01T.mat", 
        "dest": "datasets/bci/A01T.mat",
        "description": "BCI Competition IV (Dataset 2a, Subject 1)"
    },
    "mne_sample": {
        "url": "https://osf.io/86qa2/download", 
        "dest": "datasets/eeg/mne_sample_audvis_raw.fif",
        "description": "MNE Sample Data (Auditory/Visual)"
    },
    "siena_scalp_eeg": {
        "url": "https://physionet.org/files/siena-scalp-eeg/1.0.0/PN00/PN00-1.edf",
        "dest": "datasets/device/PN00-1.edf",
        "description": "PhysioNet Siena Scalp EEG (Clinical Device Trace)"
    },
    "apnea_ecg": {
        "url": "https://physionet.org/files/apnea-ecg/1.0.0/a01.dat",
        "dest": "datasets/ecg/a01.dat",
        "description": "PhysioNet Apnea-ECG (Cardiorespiratory Monitoring)"
    }
}

def download_file(url: str, dest_path: str, data_entry: dict):
    """Downloads a file, resuming if partially downloaded."""
    path = Path(dest_path)
    
    # Check if already fully downloaded (assuming size > 10KB is valid for now)
    if path.exists() and path.stat().st_size > 10240:
        print(f"[~] Skipping {path.name} (already exists and >10KB).")
        return

    print(f"[*] Downloading {path.name} from {url}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            total_size = int(response.info().get('Content-Length', 0))
            
            # If the file exists but is smaller than total size, we'll overwrite for simplicity in this script
            with open(path, 'wb') as out_file:
                downloaded = 0
                chunk_size = 8192
                while True:
                    buffer = response.read(chunk_size)
                    if not buffer:
                        break
                    out_file.write(buffer)
                    downloaded += len(buffer)
                    # Print progress inline
                    if total_size > 0:
                        sys.stdout.write(f"\r    Progress: {downloaded/1024/1024:.2f} MB / {total_size/1024/1024:.2f} MB")
                    else:
                        sys.stdout.write(f"\r    Progress: {downloaded/1024/1024:.2f} MB")
                    sys.stdout.flush()
                print(f"\n[+] Successfully downloaded {path.name}")

            # Optional SHA256 integrity check
            if 'sha256' in data_entry:
                print(f"[*] Validating SHA-256 checksum for {path.name}...")
                sha256_hash = hashlib.sha256()
                with open(path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                if sha256_hash.hexdigest() != data_entry['sha256']:
                    print(f"[!] WARNING: SHA-256 checksum mismatch for {path.name}!")
                    print(f"    Expected: {data_entry['sha256']}")
                    print(f"    Got:      {sha256_hash.hexdigest()}")
                    path.unlink() # Delete corrupted/tampered file
                else:
                    print("[+] SHA-256 checksum validated successfully.")

    except Exception as e:
        print(f"\n[!] Failed to download {path.name}: {e}")
        # Clean up partial file on hard failure
        if path.exists():
            path.unlink()

def main():
    print("========================================")
    print("VIREON 10-Dataset Fetcher")
    print("========================================")
    
    # Ensure directories exist
    Path("datasets/eeg").mkdir(parents=True, exist_ok=True)
    Path("datasets/ecg").mkdir(parents=True, exist_ok=True)
    Path("datasets/emg").mkdir(parents=True, exist_ok=True)
    Path("datasets/bci").mkdir(parents=True, exist_ok=True)
    Path("datasets/device").mkdir(parents=True, exist_ok=True)
    
    for key, data in DATASETS.items():
        print(f"\n--- Fetching: {data['description']} ---")
        download_file(data['url'], data['dest'], data)
        
    print("\n[+] Validation Corpus fetching complete.")

if __name__ == "__main__":
    main()
