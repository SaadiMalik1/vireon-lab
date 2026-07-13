# Validation: BLE Link Simulation

**Audience**: Security Researchers, Protocol Engineers

## Purpose
This document outlines how Bluetooth Low Energy (BLE) communication is simulated between the external controller and the implant.

## What is Simulated
VIREON simulates the logical state machine of a BLE Generic Attribute Profile (GATT) connection. It tracks Connection Events, MTU (Maximum Transmission Unit) sizes, and basic latency.

## Equations & Assumptions
**Assumptions**:
- **Perfect RF Channel**: We do not simulate signal attenuation due to tissue (the "body-area network" path loss). Packet loss is only simulated if explicitly triggered by the Attack Framework.
- **Infinite CPU**: We assume the implant's BLE stack can process any valid MTU size instantaneously, except when explicitly targeted by an `MTUAbuseAttack`.

## Limitations & Out of Scope
- **No PHY Layer**: VIREON does not simulate the physical RF layer (2.4 GHz). You cannot test jamming attacks that rely on overlapping radio frequencies.
- **Simplified State Machine**: We do not simulate BLE pairing or bonding crypto-exchanges. The simulation assumes the devices are already paired and bonded.

## References
This level of simulation is sufficient for modeling logical layer attacks (e.g., sending malformed GATT requests or flooding the event queue) but cannot be used to validate physical RF security.
