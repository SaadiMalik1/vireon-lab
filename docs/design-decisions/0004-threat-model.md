# ADR 0004: Explicit Threat Model Bounds

## Status
Accepted

## Context
When designing a cyber-physical simulator for neurosecurity, defining what is *in scope* for an attack is just as important as defining the attack itself. Without formal bounds, researchers might attempt to simulate unrealistic scenarios (e.g., extracting plain-text thoughts from motor-cortex EEG).

## Decision
We formally bound the VIREON threat model to the following constraints:

1. **Trust Boundaries**:
   - The Firmware is **untrusted**. We assume an attacker can achieve Remote Code Execution (RCE) on the implant.
   - The RF Link (BLE) is **untrusted**. We assume the attacker can intercept, spoof, or drop packets (e.g., MTU abuse).
   - The Patient's physiological state is **trusted** but *influenceable*. The attacker cannot directly rewrite the EEG, but they can induce physical changes (e.g., over-stimulation) that manifest as EEG alterations.

2. **Epistemic Limits**:
   - In alignment with strict clinical and neuroethics guardrails, VIREON explicitly refuses to model "mind-reading" attacks (e.g., inferring complex language from simple motor EEG). Attacks are limited to scientifically validated phenomena: Denial of Service, Battery Depletion, Tissue Heating, and broad state inference (e.g., Sleep vs. Awake).

## Consequences

### Positive
- **Scientific Integrity**: By enforcing these boundaries, VIREON maintains credibility and avoids science-fiction marketing hype.
- **Clear Scope**: Researchers know exactly what types of attacks are valid within the simulation environment.

### Negative
- **Simulation Rigidity**: Experimental researchers who want to test theoretical, unproven vectors might find the framework too restrictive.
