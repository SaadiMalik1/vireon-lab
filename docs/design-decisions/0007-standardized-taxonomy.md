# ADR 0007: Adopting Standardized Threat Taxonomies (STRIDE, MITRE)

## Status
Accepted

## Context
During the early phases of threat modeling neurotechnology, the project experimented with proprietary risk paradigms (e.g., QTARA - Quantitative Threat Analysis and Risk Assessment, OSI of Mind). While conceptually interesting, these bespoke models created severe friction when interacting with established medical device security engineers, FDA compliance teams, and academic reviewers. A novel framework acts as a barrier to entry, forcing reviewers to evaluate the framework itself rather than the results of our simulations.

## Decision
We explicitly abandon proprietary taxonomies and anchor VIREON's validation logic strictly to industry-standard cybersecurity and clinical risk frameworks.

1. **Cybersecurity Mapping**: Every simulated attack technique is mapped to the **MITRE ATT&CK** (specifically targeting ICS/Embedded behaviors) and Microsoft's **STRIDE** methodology.
2. **Vulnerability Mapping**: Where applicable, vulnerabilities are tied to the **Common Weakness Enumeration (CWE)** registry.
3. **Clinical Risk**: The validation of outcomes is framed using terms compatible with **ISO 14971** (Hazards and Harms) and **IEC 81001-5-1** (Security activities in the product lifecycle).

## Consequences

### Positive
- **Instant Credibility**: By stating an attack is a "Spoofing" event under STRIDE mapped to MITRE T0811, security engineers immediately understand the threat vector without reading a glossary.
- **Regulatory Alignment**: Medical device manufacturers can directly ingest VIREON's reports into their existing FDA premarket cybersecurity submissions, as the language matches regulatory expectations.

### Negative
- **Loss of Nuance**: Standard IT frameworks occasionally struggle to accurately describe biological phenomena (e.g., mapping "Electrode Saturation via Cognitive Interference" requires awkwardly shoehorning it into a Denial-of-Service or Tampering bucket). However, the trade-off in broader comprehension is worth the semantic mismatch.
