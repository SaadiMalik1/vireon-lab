# ADR 0008: Dynamic Spectral Calibration Profiles

## Status
Accepted

## Context
In the initial iterations of the Neuro Signal Assurance Engine (NSAE), the mathematical limits used to flag anomalies—such as maximum RMS variance or Crest Factor ceilings—were hardcoded into the Python logic. When validating against tightly controlled, artifact-free datasets (like BCI Competition data), this approach worked flawlessly. 

However, when introduced to the `Sleep-EDF` dataset, the NSAE generated a 100% False Positive Rate. The natural physiological transition from awake states to deep sleep (delta waves) caused massive, legitimate amplitude shifts that violated the rigid, hardcoded baseline constraints. Tuning the hardcoded constraints to accommodate sleep data conversely rendered the engine blind to subtle tampering in the motor-imagery datasets.

## Decision
We decoupled the baseline limits from the core engine by instituting **Dynamic Spectral Calibration Profiles**.

1. **External YAML Profiles**: Every validation dataset is assigned an explicit YAML configuration profile (e.g., `profiles/sleep_edf.yaml`) that defines the expected bounds for that specific environment (e.g., `rms_baseline`, `spectral_tolerance`).
2. **Calibration Phase**: During validation, the NSAE ingests the profile and runs an initial calibration phase over a clean segment of the EDF. It dynamically derives the EWMA (Exponentially Weighted Moving Average) and frequency bounds *before* it begins scoring anomalies.

## Consequences

### Positive
- **Honest Research**: We stop manipulating the code to hide False Positives. By transparently assigning different tolerances to different datasets, we expose exactly where the methodology excels and where it struggles.
- **Flexibility**: Researchers can test custom hardware by simply authoring a new profile reflecting their analog front-end's specific noise floor, without touching the core detection math.

### Negative
- **Setup Friction**: Validating a novel dataset now strictly requires the derivation and authoring of a configuration profile; it is no longer plug-and-play.
- **State Vulnerability**: As noted in our preprint limitations, the static nature of these profiles means the NSAE currently struggles with spontaneous, massive physiological state changes in real-time unless the profile explicitly accounts for massive variance (which degrades sensitivity).
