# NeuroShield Reference Platform

Welcome to the official documentation for **NeuroShield**, an advanced Virtual Laboratory for Brain-Computer Interface (BCI) Security and Neuroethics. NeuroShield provides a high-fidelity environment to simulate, analyze, and mitigate cyber-physical threats targeting next-generation neural interfaces.

## Overview

The rapid advancement of invasive and non-invasive BCIs introduces unprecedented security and ethical risks—from theoretical "neural ransomware" (stimulation leakage) to cognitive state inference vulnerabilities. NeuroShield is built to model these threats safely in a digital environment before they manifest in clinical reality. 

NeuroShield is an evolving research platform and reference implementation; it is mathematically and ethically aligned with the **OSI of Mind** framework and the **Quantified Interconnection Framework (QIF)** originally proposed in the [qinnovates/neurosecurity](https://github.com/qinnovates/neurosecurity) repository.

### Core Features

1. **High-Fidelity Digital Twin:** Emulates the physical constraints of an implantable/wearable BCI, including battery sag, ADC saturation, electrode impedance variance, and thermal tissue constraints.
2. **Deep Learning NeuroIDS:** An onboard Intrusion Detection System that falls back gracefully from a PyTorch-based Deep Autoencoder to a lightweight Numpy-based Linear Autoencoder, detecting anomalies in sub-millisecond windows.
3. **qTARA Threat Intelligence:** Directly integrates the 161-technique TARA (Threat Assessment & Remediation Analysis) registry to map mathematical anomalies to real-world threat vectors (e.g., QIF-T0001).
4. **Neuroethics Guardrails:** Enforces the "8 Guardrails of Neuromodesty" (e.g., G1), refusing to compile or simulate scientifically unfounded "mind-reading" attacks, maintaining strict epistemic integrity.
5. **Runemate Compiler:** A safe, embedded Rust-based DSL compiler (`Forge` and `Scribe`) for executing clinical therapies and testing bounded memory safety.

---

## Documentation Navigation

This documentation is divided into extensive standalone guides:

- **[System Architecture](architecture.md)**: Deep dive into the Digital Twin physics engine, Coordinator orchestration, and Runemate Rust compiler.
- **[Threat Modeling](threat-model/README.md)**: Comprehensive explanation of the NeuroIDS, Attack Surface, and how the qTARA Threat Intelligence is parsed.
- **[API & Interfaces](api.md)**: Python API reference, CLI commands, and Telemetry structures.
- **[Plugin Development Guide](plugin-development.md)**: How to write custom Attack and Device plugins via the Event Bus.
- **[QIF Derivation Log](QIF-DERIVATION-LOG.md)**: The central architectural decision record tracing changes back to the original OSI of Mind governance.
- **[Glossary & Formal Definitions](glossary.md)**: Mathematical and structural bounds defining the scope of theoretical attacks.
- **[Frequently Asked Questions](FAQ.md)**: Troubleshooting installation, dashboards, and stream capturing.

---

## Quickstart Guide

### Prerequisites
- Python 3.10+
- Optional: `torch` (for DeepAutoencoderIDS support)
- Optional: `weasyprint` (for PDF report generation)
- Rust toolchain (for compiling the Runemate DSL)

### Running the Virtual Laboratory

NeuroShield can be launched directly via its CLI using `click`. The default mode runs a 10-second simulation:

```bash
# Run a 10-second simulation with an active noise attack
python3 -m neuroshield run --duration 10.0 --attack noise
```

### Accessing the Web Dashboard

NeuroShield serves a rich diagnostic dashboard built with Streamlit:

1. Launch the dashboard:
   ```bash
   python3 -m neuroshield ui --port 7777
   ```
2. Open your browser and navigate to `http://localhost:7777`.
3. View real-time EEG traces, Digital Twin physical metrics, and active qTARA Threat Intelligence alerts.

---

*NeuroShield is an open-source project dedicated to the safe, transparent, and ethical advancement of neural engineering.*

## Acknowledgments / Inspiration

We would like to give a massive shout-out to the [qinnovates/neurosecurity](https://github.com/qinnovates/neurosecurity) repository! NeuroShield drew heavy inspiration from their foundational work. We built upon the architectural proposals, ethical frameworks, and advanced neurosecurity ideas described in their project to make this virtual laboratory a reality.
