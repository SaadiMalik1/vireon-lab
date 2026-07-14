# Attack Surface

**Audience**: Security Researchers, Developers

This document maps the exposed logical and physical interfaces of the simulated VIREON medical implant that an attacker could target.

## 1. Firmware OTA Interface
The Over-The-Air (OTA) update mechanism allows external controllers to flash new firmware to the implant.
- **Vulnerabilities Simulated**: Firmware Rollback (bypassing the Anti-Rollback eFuse checks), Malicious Payload Injection.
- **Defenses Evaluated**: Secure Boot verification, Zero-Trust Architecture (ZTA) context checks, Monotonic SVN counters.

## 2. BLE GATT Server
The Bluetooth Low Energy (BLE) interface exposes services for telemetry streaming and therapy configuration.
- **Vulnerabilities Simulated**: MTU Abuse (flooding the event queue with oversized or malformed Maximum Transmission Unit requests leading to DoS).
- **Defenses Evaluated**: Rate limiting, strict MTU bounds checking.

## 3. Telemetry Egress
The streams (LSL and WebSockets) transmitting the patient's biological data.
- **Vulnerabilities Simulated**: Eavesdropping, Cognitive State Inference (analyzing patterns in the unencrypted stream).
- **Defenses Evaluated**: End-to-End Encryption (E2EE), Zero-Trust Architecture (ZTA) data egress blocking.

## 4. Therapy Execution Engine (NeuroDSL)
The embedded DSL interpreter responsible for safely executing clinical therapies.
- **Vulnerabilities Simulated**: Memory corruption, Infinite loop execution causing battery drain.
- **Defenses Evaluated**: NeuroDSL Rust compiler memory bounds, Execution timeouts.
