# VIREON Derivation Log

This document serves as the single source of truth for architectural decisions in the VIREON platform, tracking its alignment with clinical and cybersecurity industry standards.

## Entry 001
**Date:** 2026-07-09
**Architectural Decision:** Standards-Based Threat Intelligence Integration
**Context:** Needed a realistic threat modeling baseline for simulated attacks.
**Derivation:** Integrated standard cybersecurity taxonomy (`standards_mapping.json`) directly into the `Coordinator` via `ThreatIntelligence`. Anomalies mapped to physical signatures are now cross-referenced against STRIDE, MITRE CWE, and IEC 62304.
**Guardrail Enforced:** G5 (Conceptual Underspecification). We rely on published physical attack techniques rather than vague descriptions of generic anomalies.

## Entry 002
**Date:** 2026-07-09
**Architectural Decision:** Neuroethics Guardrail Enforcement Engine
**Context:** Need to prevent the simulation engine from being used to validate unrealistic or offensive neuro-hacking claims.
**Derivation:** Added `GuardrailValidator` to the setup phase of `Coordinator`. Any configuration or active attack that claims cognitive decoding (e.g. "thought reading") is rejected before the simulation starts.
**Guardrail Enforced:** G1 (Neuromodesty), G6 (Brain Reading Limits), G7 (Dual-Use Trap).

