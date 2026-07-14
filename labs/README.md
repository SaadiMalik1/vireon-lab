# VIREON Practical Labs

Theory alone isn't enough. The VIREON Labs are designed to give you hands-on experience bridging the knowledge base concepts with actionable simulation execution.

## Available Labs

### [Lab 1: Signal Ingestion & Baseline Calibration](lab-01-signal-ingestion/)
- **Goal**: Load a raw EDF dataset and observe how the Neuro Signal Assurance Engine (NSAE) establishes a dynamic spectral baseline.
- **Concepts Applied**: EEG, Signal Processing, File Parsing.

### [Lab 2: Artifact Injection & Signal Spoofing](lab-02-artifact-injection/)
- **Goal**: Use the CLI to explicitly inject localized noise into an active simulation to see how the NSAE detects non-physiological anomalies.
- **Concepts Applied**: Fast Fourier Transform (FFT), Threat Modeling (Injection).

### [Lab 3: Anomaly Detection & Policy Degradation](lab-03-anomaly-detection/)
- **Goal**: Run a full simulation where a BLE MTU flooding attack causes the Zero Trust Policy Engine to degrade the connection, halting telemetry egress.
- **Concepts Applied**: Bluetooth Low Energy (BLE), Digital Twin Physics, Denial of Service.

*(See the `README.md` inside each lab directory for step-by-step commands using `vireon run`).*
