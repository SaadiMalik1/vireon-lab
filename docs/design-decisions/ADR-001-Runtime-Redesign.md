# Architecture Decision Record: 001 - Runtime Redesign and DigitalTwin Deprecation

## Status
**Accepted**

## Context
VIREON was initially built as an educational simulator relying on a monolithic `Coordinator` and a central `DigitalTwin` God class. As the framework evolves toward a vendor-neutral validation platform (a "ROS for neurotechnology"), the monolithic architecture prevents scalability, security, and true vendor isolation. Plugins were tightly coupled to the internal state of the `DigitalTwin`, meaning any changes to the core physics or state representation broke all plugins.

Additionally, to execute untrusted, proprietary binaries (e.g., vendor firmware or proprietary ML decoders), we needed a mechanism to isolate plugins without giving them full access to the simulation state.

## Decision
1. **Dismantle the `Coordinator` and `DigitalTwin`:** We replace the `Coordinator` with a lightweight `Orchestrator`. We replace the `DigitalTwin` with a decentralized `StateStore`.
2. **Introduce the `EventBus`:** All cross-module communication is now handled via pub/sub events rather than direct method calls.
3. **Establish the `IProvider` Interface:** All plugins must implement `IProvider` and define a `CapabilityManifest`.
4. **Implement Capability-Based Security:** Plugins are only granted access to the specific state keys and event topics declared in their manifest, enforced by the `CapabilityEngine`.
5. **Support Subprocess Isolation:** Untrusted plugins run via the `SubprocessProvider` in separate OS processes using JSON-RPC over `stdin/stdout`.

## Consequences

### Positive
* **Vendor Neutrality:** Vendors can integrate proprietary binaries via the `SubprocessProvider` without sharing source code.
* **Security:** Capability-based access control prevents malicious or buggy plugins from corrupting the entire simulation state.
* **Modularity:** Physics engines, decoders, and hardware bridges are now interchangeable plugins rather than hardcoded core dependencies.

### Negative
* **Migration Overhead:** Existing plugins must be rewritten to conform to the `IProvider` interface and use asynchronous event handling instead of synchronous state mutations.
* **Performance:** Relying on the `EventBus` and IPC for high-frequency data (like raw EEG streams) incurs serialization and context-switching overhead compared to direct memory access. (Future mitigation: Zero-copy shared memory).
