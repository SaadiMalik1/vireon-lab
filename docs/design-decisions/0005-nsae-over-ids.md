# ADR 0005: Shifting from IDS to a Neuro Signal Assurance Engine (NSAE)

## Status
Accepted

## Context
Traditional cybersecurity models for connected medical devices rely heavily on network Intrusion Detection Systems (IDS). These systems analyze packet structures, RF metadata, and encrypted protocol behaviors (e.g., BLE MTU lengths) to infer adversarial activity. 

Initially, VIREON adopted the "NeuroIDS" nomenclature. However, as the threat model evolved to encompass analog and physical-layer attacks (e.g., localized electrode heating, electromagnetic interference, adversarial neural stimulation), it became evident that a standard network IDS paradigm was fundamentally insufficient. Packet-level analysis cannot detect a physically induced signal saturation event occurring before the Analog-to-Digital Converter (ADC).

## Decision
We formally transition the core security component from a "NeuroIDS" to a **Neuro Signal Assurance Engine (NSAE)**. 

1. **Boundary Shift**: The primary detection boundary is moved from the network/telemetry layer directly to the raw physiological signal layer (the continuous EEG stream).
2. **Methodological Shift**: Detection relies on mathematical characterization of the signal's physics (e.g., Crest Factor, RMS, Spectral Density, Envelope constraints) rather than signature-based packet matching.
3. **Nomenclature**: The term "Assurance" accurately reflects the engine's purpose: verifying the clinical and physical integrity of the telemetry rather than merely detecting network intrusions.

## Consequences

### Positive
- **Physical-Layer Threat Detection**: VIREON can now successfully detect complex physical attacks (e.g., induced tissue heating altering impedance, external EMI) that a network IDS would completely miss.
- **Scientific Clarity**: "NSAE" communicates to clinical researchers and neuro-engineers that the validation is grounded in physiology and signal processing, not just IT security.

### Negative
- **Computational Overhead**: Continuous spectral and mathematical analysis of multi-channel EEG arrays requires more compute than lightweight packet filtering.
- **Nomenclature Education**: Users familiar with traditional IT security will require documentation to understand why the term IDS was explicitly abandoned.
