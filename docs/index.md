# VIREON Reference Platform

Welcome to the official documentation for **VIREON**, an advanced Virtual Laboratory for Brain-Computer Interface (BCI) Security and Neuroethics. VIREON provides a high-fidelity environment to simulate, analyze, and mitigate cyber-physical threats targeting next-generation neural interfaces.

## Overview

The rapid advancement of invasive and non-invasive BCIs introduces unprecedented security and ethical risks—from theoretical "neural ransomware" (stimulation leakage) to cognitive state inference vulnerabilities. VIREON is built to model these threats safely in a digital environment before they manifest in clinical reality. 

VIREON is an evolving research platform and reference implementation; it is mathematically and ethically aligned with established industry standards (STRIDE, MITRE CWE, IEC 62304) and the **VIREON Validation Profile**.

### Core Features

1. **High-Fidelity State Store:** Emulates the physical constraints of an implantable/wearable BCI, including battery sag, ADC saturation, electrode impedance variance, and thermal tissue constraints.
2. **Deep Learning SecurityEngine:** An onboard Intrusion Detection System that falls back gracefully from a PyTorch-based Deep Autoencoder to a lightweight Numpy-based Linear Autoencoder, detecting anomalies in sub-millisecond windows.
3. **Standards-Based Threat Intelligence:** Directly integrates with established cybersecurity frameworks (STRIDE, MITRE) to map mathematical anomalies to real-world threat vectors.
4. **Neuroethics Guardrails:** Enforces the "8 Guardrails of Neuromodesty" (e.g., G1), refusing to compile or simulate scientifically unfounded "mind-reading" attacks, maintaining strict epistemic integrity.
5. **Strict Ecosystem Separation:** Employs a decoupled core engine with strict capability boundaries to support un-trusted vendor firmware plugins.

---

## Documentation Navigation

This documentation is divided into extensive standalone guides:

### 1. Architecture & Ecosystem Design
- **[Architectural Boundaries](ARCHITECTURAL_BOUNDARIES.md)**: Strict ownership mapping separating `vireon` (Framework/SDK) and `vireon_lab` (Educational).
- **[Plugin Lifecycle Management](PLUGIN_LIFECYCLE.md)**: The 10-phase state machine that safely discovers, validates, and spins up third-party plugins.
- **[Configuration Architecture](CONFIGURATION_ARCHITECTURE.md)**: Details on the declarative YAML configurations that govern threat models and capabilities.
- **[Testing Architecture](TESTING_ARCHITECTURE.md)**: Explains the multi-layered testing paradigm used to validate external plugins and the core engine.
- **[Versioning Strategy](VERSIONING_STRATEGY.md)**: SemVer guidelines to ensure external plugins remain compatible across SDK releases.

### 2. Development & Integration
- **[API & Interfaces](api.md)**: Python API reference detailing the `vireon.sdk` contracts and `vireon.core` orchestration.
- **[Plugin Development Guide](plugin-development.md)**: How to write custom Firmware Providers and capabilities using `IVireonPlugin`.

### 3. Theory & Mechanics
- **[Physics Constraints](physics.md)**: Physics boundary conditions and integration limits for the simulations.
- **[Threat Modeling](threat-model/README.md)**: Comprehensive explanation of the SecurityEngine, Attack Surface, and how the standards-based Threat Intelligence is parsed.
- **[Standards Derivation Log](STANDARDS-DERIVATION-LOG.md)**: The central architectural decision record tracing the alignment with clinical and cybersecurity industry standards.
- **[Glossary & Formal Definitions](glossary.md)**: Mathematical and structural bounds defining the scope of theoretical attacks.
- **[Frequently Asked Questions](faq.md)**: Troubleshooting installation, dashboards, and stream capturing.

---

## Quickstart Guide

### Prerequisites
- Python 3.10+
- Optional: `torch` (for DeepAutoencoderIDS support)
- Optional: `weasyprint` (for PDF report generation)
- Rust toolchain (for compiling the NeuroDSL DSL)

### Running the Virtual Laboratory

VIREON can be launched directly via its CLI using `click`. The default mode runs a 10-second simulation:

```bash
# Run a 10-second simulation with an active noise attack
python3 -m vireon run --duration 10.0 --attack noise
```

### Accessing the Web Dashboard

VIREON serves a rich diagnostic dashboard built with Streamlit:

1. Launch the dashboard:
   ```bash
   python3 -m vireon ui --port 7777
   ```
2. Open your browser and navigate to `http://localhost:7777`.
3. View real-time EEG traces, State Store physical metrics, and active standards-based Threat Intelligence alerts.

---

*VIREON is an open-source project dedicated to the safe, transparent, and ethical advancement of neural engineering.*

## Acknowledgments / Inspiration

VIREON builds upon principles of safe neurotechnology and secure embedded systems design, translating high-level frameworks like STRIDE and FDA pre-market guidelines into executable clinical simulations.
