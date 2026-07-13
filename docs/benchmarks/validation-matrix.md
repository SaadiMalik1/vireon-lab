# VIREON Validation Matrix

**Audience**: Academic Researchers, Reviewers

VIREON maps its core modules to specific, curated datasets. Rather than arbitrarily testing against random recordings, every dataset in our corpus serves a precise validation target.

## Active Mapping

| Module | Dataset Target | Provenance | Status |
| :--- | :--- | :--- | :--- |
| **EEG Preprocessing** | MNE Sample | [MNE-Python](https://mne.tools/stable/datasets.html) | Planned |
| **EEG Replay** | PhysioNet EEG (MMI) | [PhysioNet](https://physionet.org/content/eegmmidb/1.0.0/) | Planned |
| **Motor Imagery** | BCI Competition IV | [BCI Competition](https://www.bbci.de/competition/iv/) | Planned |
| **Signal Filtering** | OpenBCI Examples | [OpenBCI](https://openbci.com/) | Planned |
| **Artifact Removal** | Sleep-EDF | [PhysioNet](https://physionet.org/content/sleep-edfx/1.0.0/) | Planned |
| **Anomaly Detection (IDS)** | Synthetic + PhysioNet | In-house generator | Planned |
| **Protocol Replay** | BLE PCAP Captures | In-house/Extracted | Planned |

## Automated Validation
VIREON is currently building the `vireon validate` CLI tool. This command will automatically:
1. Fetch missing datasets from their respective canonical sources.
2. Verify checksums.
3. Preprocess the raw traces according to the module requirements.
4. Execute the targeted simulation/replay against the dataset.
5. Generate a reproducible HTML/PDF performance benchmark report.
