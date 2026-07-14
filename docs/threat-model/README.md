# Threat Modeling

This directory contains the formal threat model for the VIREON simulation environment. We strictly define the boundaries of our simulations to ensure scientific and engineering rigor, avoiding theoretical scenarios that lack physiological or physical backing.

## Documents

1. **[Assumptions & Trust Boundaries](assumptions.md)**: Defines what is considered trusted vs untrusted within the simulation environment, including epistemic boundaries (what attacks are considered scientifically valid).
2. **[Attack Surface](attack-surface.md)**: A detailed mapping of the vectors an attacker can leverage in the simulation (e.g., Firmware OTA interface, BLE GATT Server).
3. **[Standards Mapping Registry](../core/data/standards_mapping.json)**: An index explaining how VIREON validation profiles map to established frameworks like STRIDE, MITRE ATT&CK, CWE, and ISO 14971.
