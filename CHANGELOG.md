# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0-alpha] - Phase 9 Architecture Implementation

### Added
- `vireon.core.orchestrator.Orchestrator` as the new thin runtime replacing the monolithic `Coordinator`.
- `vireon.core.state_store.StateStore` providing a decentralized, thread-safe blackboard for cross-plugin state sharing.
- `vireon.core.event_bus.EventBus` enabling completely decoupled, pub/sub inter-plugin communication.
- `vireon.sdk.interfaces.IProvider` specifying the unified Plugin SDK interface.
- `vireon.sdk.manifest.CapabilityManifest` allowing capability negotiation and runtime dependency injection.
- `vireon.sdk.subprocess_provider.SubprocessProvider` enforcing Level 1 Isolation via standard JSON-RPC over `stdin/stdout`.
- `vireon.core.capability_engine.CapabilityEngine` governing plugin access to the system via capability proxies.

### Changed
- Refactored `ReplayEngine` to eliminate dependencies on `DigitalTwin` and hardcoded physics simulations.
- Ported `ClosedLoopSimulator` and `CortexMStub` to the new `IProvider` architecture.
- Deprecated direct dependencies on the legacy `DigitalTwin` God class.

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
