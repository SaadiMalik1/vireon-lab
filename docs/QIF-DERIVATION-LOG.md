# VIREON Derivation Log

This document serves as the single source of truth for architectural decisions in the VIREON platform, adopting the governance model of the original Quantified Interconnection Framework (QIF).

## Entry 001
**Date:** 2026-07-09
**Architectural Decision:** TARA Integration
**Context:** Needed a realistic threat modeling baseline for simulated attacks.
**Derivation:** Integrated the full 161-technique TARA dataset (`qtara-registrar.json`) directly into the `Coordinator` via `ThreatIntelligence`. Anomalies mapped to physical signatures are now cross-referenced against this registry.
**Guardrail Enforced:** G5 (Conceptual Underspecification). We rely on published physical attack techniques rather than vague descriptions of generic anomalies.

## Entry 002
**Date:** 2026-07-09
**Architectural Decision:** Neuroethics Guardrail Enforcement Engine
**Context:** Need to prevent the simulation engine from being used to validate unrealistic or offensive neuro-hacking claims.
**Derivation:** Added `GuardrailValidator` to the setup phase of `Coordinator`. Any configuration or active attack that claims cognitive decoding (e.g. "thought reading") is rejected before the simulation starts.
**Guardrail Enforced:** G1 (Neuromodesty), G6 (Brain Reading Limits), G7 (Dual-Use Trap).

