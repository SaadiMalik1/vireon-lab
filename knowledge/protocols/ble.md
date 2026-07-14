# Bluetooth Low Energy (BLE)

## What is it?
Bluetooth Low Energy (BLE) is a wireless personal area network technology designed for significantly reduced power consumption while maintaining a similar communication range to classic Bluetooth.

## Why does it matter?
Because of strict power constraints (implant batteries cannot easily be replaced) and tissue attenuation limits, almost all modern implantable and wearable neurotechnology rely on BLE for communication with external mobile devices or base stations.

## Security Considerations
BLE dictates the primary wireless attack surface for medical devices. Security relies on the Pairing/Bonding phase. If a device supports "Just Works" pairing without out-of-band (OOB) authentication or cryptographic verification, it is highly susceptible to unauthenticated interception and spoofing.

## Common Vulnerabilities
- **MTU Abuse**: Crashing the implant's communication stack by negotiating malformed Maximum Transmission Unit (MTU) sizes.
- **Man-in-the-Middle (MitM)**: Intercepting the GATT (Generic Attribute Profile) exchanges if pairing is unencrypted.
- **Battery Drain**: Flooding the device with continuous connection requests to prevent it from entering a sleep state (Denial of Service).

## Relevant Standards
- **Bluetooth SIG Specifications**: Core Spec v4.0 through v5.4.
- **NIST SP 800-121**: Guide to Bluetooth Security.

## Real Devices
- Virtually all consumer BCIs (Muse, Emotiv, OpenBCI via Bluetooth dongle).
- Modern implantable pulse generators communicating with patient smartphones.

## Where VIREON uses this concept
VIREON implements a dedicated `BLEEmulator` (`vireon/plugins/ble/emulator.py`) to simulate these exact vectors. By modeling connection flooding and malformed GATT exchanges, the **Digital Twin** reflects excessive battery drain and CPU spikes. The `VulnerabilityMonitor` (`vireon/plugins/reports/vulnerability_monitor.py`) then asserts whether the implant's fail-safes (e.g., shutting off the radio to preserve therapy power) activate correctly under sustained BLE assault.

## Further reading
- [Neuroscience: DBS](../neuroscience/dbs.md)
