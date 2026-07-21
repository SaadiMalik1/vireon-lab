# VIREON Lab Scripts

This directory contains various utility scripts for managing datasets and running experiments within the VIREON Lab environment.

## `fetch_public_datasets.py`

The **VIREON 10-Dataset Fetcher** is a utility script that automatically downloads curated public datasets required for the Validation Suite. 

These datasets are used to validate and benchmark the neurotechnology validation framework across various physiological signals.

### Supported Datasets

The script fetches the following datasets:
1. **PhysioNet EEG MMI**: Subject 1 Baseline (`eegmmi_baseline`) and Motor Imagery (`eegmmi_imagery`)
2. **PhysioNet Sleep-EDF**: Subject 0, Cassette 1 (`sleep_edf`)
3. **PhysioNet CHB-MIT**: Epilepsy, Subject 1 (`chb_mit_epilepsy`)
4. **PhysioNet MIT-BIH Arrhythmia**: Record 100 (`mit_bih_ecg`)
5. **PhysioNet EMG**: Healthy Baseline (`emg_healthy`)
6. **BCI Competition IV**: Dataset 2a, Subject 1 (`bci_comp_iv`)
7. **MNE Sample Data**: Auditory/Visual (`mne_sample`)
8. **PhysioNet Siena Scalp EEG**: Clinical Device Trace (`siena_scalp_eeg`)
9. **PhysioNet Apnea-ECG**: Cardiorespiratory Monitoring (`apnea_ecg`)

### Features
- **Resumable Downloads**: The script will automatically skip files that already exist and have a size greater than 10KB.
- **SSL Bypass**: Bypasses SSL verification errors common in strict or locked-down environments.
- **Integrity Checking**: Validates SHA-256 checksums if provided in the dataset dictionary to ensure data hasn't been tampered with or corrupted during download.

### Usage

Run the script from the root of the `vireon-lab` repository:

```bash
python scripts/fetch_public_datasets.py
```

The script will create the necessary directory structure (`datasets/eeg`, `datasets/ecg`, `datasets/emg`, `datasets/bci`, `datasets/device`) and download the files into their respective locations.
