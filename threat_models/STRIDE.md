# STRIDE Threat Modeling Mapping

This document maps the STRIDE threat categories to the simulated vulnerabilities and mitigations within the VIREON environment.

| STRIDE Category | Description | Simulated Vulnerability | Mitigation |
|---|---|---|---|
| **Spoofing** | Impersonating something or someone else. | Spoofed BLE connection or clinician programmer. | NSAE Authentication (simulated in `core/detection.py`), E2EE. |
| **Tampering** | Modifying data or code. | Malicious firmware update (OTA Tampering). | Signature Verification in `cortex_m_stub.py`. |
| **Repudiation** | Claiming to have not performed an action. | Clinical parameter changes without logs. | Immutable state logging in `twin.py` history. |
| **Information Disclosure** | Exposing information to unauthorized individuals. | Neural data interception over BLE. | E2EE encryption of neural payloads (`e2ee.py`). |
| **Denial of Service** | Denying or degrading service to users. | Battery drain attack (Peukert's Law). | Firmware Fallback Mode, IPS rate limiting (`core/detection.py`). |
| **Elevation of Privilege** | Gaining capabilities without proper authorization. | Exploiting debugger interface to read/write memory. | Memory isolation, clinical risk checks (`core/clinical.py`). |

## Notes
The STRIDE model is applied to both the simulated Digital Twin (Vireon) and the physical threat models represented in the YAML definitions.
