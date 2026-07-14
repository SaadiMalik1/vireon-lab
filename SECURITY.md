# Security Policy

**Audience**: Security Researchers, Developers

## Purpose
This document outlines the security assumptions, threat model of the repository itself, and the responsible disclosure policy for reporting vulnerabilities in the NeuroShield framework.

## Scope
This policy applies to the NeuroShield engine, its core plugins, and the NeuroDSL compiler. It does **not** cover vulnerabilities found in the third-party medical hardware simulated by NeuroShield (e.g., OpenBCI boards, Medtronic pacemakers).

## Threat Model & Security Assumptions
NeuroShield is a *research and simulation* tool. 
- **Trust Boundary**: The local execution environment is assumed to be trusted. We do not currently sandbox the execution of user-provided Python plugins beyond standard OS permissions.
- **NeuroDSL DSL**: The embedded Rust compiler (`NeuroDSL`) is designed to provide bounded memory safety for simulated clinical therapies, but is not intended to securely sandbox malicious arbitrary code execution on the host machine.
- **Telemetry Egress**: LSL and WebSocket streams emitted by NeuroShield are unencrypted by default (unless ZTA/E2EE layers are explicitly enabled in the simulation config). They should not be exposed to untrusted networks.

## Supported Versions
Only the latest release on the `main` branch is actively supported for security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

We take the security of NeuroShield seriously. If you discover a security vulnerability in the NeuroShield platform, please **do not** report it via public GitHub issues.

Instead, please send an email to **security@neuroshield-project.org**.

### What to include
- A description of the vulnerability.
- Steps to reproduce the vulnerability.
- Proof of Concept (PoC) code or scripts, if applicable.
- The impact of the vulnerability.

### Response Timeline
- We will acknowledge receipt of your vulnerability report within 48 hours.
- We aim to provide a resolution or mitigation plan within 7 days.
- We will coordinate public disclosure with you after the fix has been pushed.

## Out-of-Scope Attacks
- Denial of Service (DoS) attacks requiring massive external resources against the simulation host.
- Social engineering of NeuroShield contributors.
- Vulnerabilities in upstream dependencies (e.g., NumPy, PyTorch), unless NeuroShield uses them in an egregiously insecure manner.

## Related Documents
- [Contributing Guidelines](CONTRIBUTING.md)
- [System Architecture](docs/architecture.md)
