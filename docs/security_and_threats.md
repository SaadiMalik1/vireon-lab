# Security & Threat Modeling

NeuroShield is engineered around a realistic, ethically constrained threat model. It integrates advanced machine learning anomaly detection with the real-world **Quantified Threat Assessment and Remediation Analysis (qTARA)** registry developed by the OSI of Mind project.

## 1. NeuroIDS: The Intrusion Detection System

Located in `security.py`, `NeuroIDS` acts as the active security shield monitoring the Digital Twin's physiological data streams.

### Dynamic Backend Selection
To balance accuracy with computational overhead, `NeuroIDS` dynamically scales its detection backend:

- **DeepAutoencoderIDS (PyTorch)**: If the `torch` module is available, NeuroShield utilizes a deep neural network consisting of multi-layered encoding/decoding blocks (e.g., `[input_dim, 64, 32, 16]`). This allows it to capture highly non-linear anomalies in the multiplexed EEG streams.
- **LinearAutoencoderIDS (Numpy Fallback)**: If PyTorch is unavailable, the system transparently falls back to a custom, dependency-light numpy implementation acting as an online PCA (Principal Component Analysis). It uses an orthogonal weight projection to identify linear deviations from nominal baselines.

Both backends utilize a dynamic thresholding mechanism (`mse_threshold * 1.5` scaling) to adapt to the baseline noise of the specific simulated BCI board.

### Coherence Engine
The `CoherenceEngine` verifies physiological expectations. If an attacker injects a command to increase stimulation amplitude, the engine expects to see a corresponding autonomic response (e.g., pupil dilation). If the command executes but the physiological response is missing, the `CoherenceEngine` flags a `GHOST_STIMULATION_ATTACK`.

## 2. qTARA Threat Intelligence

Simulated mathematical anomalies (e.g., `SLOW_DRIFT`, `SPIKE_NOISE`) are inherently meaningless without context. NeuroShield grounds these anomalies using the `ThreatIntelligence` module (`threat_intel.py`).

### Registry Parsing
Upon initialization, NeuroShield ingests the 1MB `qtara-registrar.json` datalake file. This file contains 161 highly detailed, peer-reviewed neurosecurity threat vectors, categorized into physical, hardware, and logical attacks.

### Real-Time Mapping
When `NeuroIDS` detects an anomaly:
1. It identifies the spatial origin (e.g., "Prefrontal Cortex" on Channel 0).
2. It classifies the mathematical anomaly (e.g., `SLOW_DRIFT_ANOMALY`).
3. The `ThreatIntelligence` module cross-references this signature against the qTARA registry.
4. The generic anomaly is upgraded to a concrete threat object (e.g., **"QIF-T0001: Sub-threshold Signal Injection"**), pulling in its CVSS score, mitigation strategies, and Neuromodesty implications.

This enriched threat object is then broadcast over telemetry to the Web Dashboard.

## 3. Neuroethics Guardrails

NeuroShield strictly adheres to the **Quantified Interconnection Framework (QIF)** ethical boundaries, specifically preventing the simulation from being used to validate pseudoscientific claims.

### The GuardrailValidator (`guardrails.py`)
Before any simulation begins, the `Coordinator` passes the `ExperimentConfig` through the `GuardrailValidator`. 

The validator actively blocks scenarios that violate **G1: Neuromodesty**:
- It searches for banned conceptual strings in the configuration (e.g., `"read_mind"`, `"password_extraction"`, `"cognitive_override"`).
- If an attacker specifies a "thought extraction" payload, the validator aborts the boot sequence with a `GuardrailViolation`.
- NeuroShield only allows the simulation of physical disruptions (e.g., ADC saturation, battery drainage, tissue heating, DOS), refusing to model the decoding of high-level cognitive states, maintaining rigorous epistemic integrity.
