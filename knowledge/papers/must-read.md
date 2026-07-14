# Publications

This document tracks academic and technical publications associated with the VIREON project and foundational literature in the field of neuro-security.

*(Currently, refer to `docs/technical-report.md` for our primary preprint outlining the Neuro Signal Assurance Engine (NSAE) architecture and validation).*

## Foundational Literature in Neuro-Security

The threat model and physical-layer validation approaches in VIREON are heavily influenced by the following seminal works:

- **Denning, T., Matsuoka, Y., & Kohno, T. (2009). "Neurosecurity: security and privacy for neural devices."** *Neurosurgical Focus*.
  - *Relevance to VIREON*: This paper formally introduced the concept of "neurosecurity," establishing the critical need for confidentiality, integrity, and availability in neural interfaces. It frames our core motivation for building an assurance engine.

- **Halperin, D., et al. (2008). "Pacemakers and Implantable Cardiac Defibrillators: Software Radio Attacks and Zero-Power Defenses."** *IEEE Symposium on Security and Privacy*.
  - *Relevance to VIREON*: Demonstrated real-world wireless vulnerabilities in implantable medical devices (IMDs) using software-defined radios. It inspired VIREON's BLE/RF telemetry threat models (e.g., unauthorized control, battery depletion).
