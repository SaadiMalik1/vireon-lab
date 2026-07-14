# VIREON Validation Matrix

**Audience**: Academic Researchers, Reviewers

VIREON maps its core modules to specific, curated datasets. Rather than arbitrarily testing against random recordings, every dataset in our corpus serves a precise validation target.

## Active Mapping

| Module | Dataset Target | Provenance | Status |
| :--- | :--- | :--- | :--- |
| **EEG Baseline** | PhysioNet EEG MMI (S001R01) | [PhysioNet](https://physionet.org/content/eegmmidb/1.0.0/) | Validated |
| **Motor Imagery** | PhysioNet EEG MMI (S001R04) | [PhysioNet](https://physionet.org/content/eegmmidb/1.0.0/) | Validated |
| **Clinical Seizure** | CHB-MIT Epilepsy (chb01_03) | [PhysioNet](https://physionet.org/content/chbmit/1.0.0/) | Validated |
| **Polysomnography** | Sleep-EDF (SC4001E0) | [PhysioNet](https://physionet.org/content/sleep-edfx/1.0.0/) | Validated |
| **Device Artifacts** | Siena Scalp EEG (PN00-1) | [PhysioNet](https://physionet.org/content/siena-scalp-eeg/1.0.0/) | Validated |
| **Synthetic Attacks** | Noise & Packet Loss | In-house generator | Validated |
| **Protocol Replay** | BLE PCAP Captures | In-house/Extracted | Planned |

## Automated Validation
VIREON implements the `vireon validate` CLI tool. This command automatically:
1. Loads the downloaded EDF files using a zero-dependency pure-Python EDF reader.
2. Calibrates the engine dynamically by extracting dataset-specific spectral characteristics.
3. Feeds clean windows through the VIREON engine to measure baseline false-positive rates.
4. Applies simulated adversarial mutations (e.g., noise injection, signal drift) and measures true detection rates.
5. Generates a reproducible, computed JSON performance benchmark report.
