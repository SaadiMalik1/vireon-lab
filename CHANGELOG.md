# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Embedded Rust compiler (NeuroDSL) for clinical therapy synthesis.
- Zero-Trust Policy Engine for analyzing streams.
- Deep Autoencoder IDS for anomaly detection.

### Changed
- Complete architectural decomposition of the `Coordinator` into `SimulationBuilder` and event-driven `CoordinatorCallbacks`.
- Refactored `security.py` into dedicated detection modules: `core/detection.py`.
- Modernized cryptography using standard library algorithms (ECDH, SHA256, AES-GCM) instead of simulated stubs.
- Updated threat modeling capabilities to dynamically align with MITRE CWE and STRIDE standards.

### Deprecated
- `security.py` (logic has been split).
- Inline simulation callbacks in the main `Coordinator` class.

### Fixed
- Fixed internal documentation links and structural consistency across the repository.
- Rectified Python versions and Rust toolchain requirements for builds.
- Refactored the core physics loop for stability and performance.
