# Versioning Strategy

## Overview
VIREON follows a strict versioning architecture to ensure that the orchestration runtime and the vendor plugin ecosystem can evolve independently without causing ecosystem fragmentation.

This document outlines the versioning philosophy, compatibility guarantees, and capability translation layers.

## The Three Tiers of Versioning

VIREON maintains three decoupled versioning domains:

1. **Core Runtime Semantic Versioning (SemVer)**
2. **Provider SDK Interface Versioning**
3. **Capability Manifest Versioning**

---

### 1. Core Runtime (SemVer)
The framework itself (`vireon-core`) strictly adheres to Semantic Versioning (`MAJOR.MINOR.PATCH`).
- **MAJOR**: Breaking changes to CLI arguments, orchestrator architecture, or the `EventBus` underlying implementation.
- **MINOR**: New capabilities added to the Capability Engine, new built-in tools, or performance optimizations.
- **PATCH**: Bug fixes and security patches.

### 2. Provider SDK Interface
The `IProvider` interface and IPC schemas evolve separately from the core framework.
When an SDK interface changes (e.g., changing the IPC standard from JSON-RPC to gRPC):
- It is tracked as `SDK_v1`, `SDK_v2`, etc.
- **Rule**: The Orchestrator must support at least one prior major SDK version via Translation Adapters.

### 3. Capability Manifest
The YAML/JSON schema defining capabilities (`CapabilityManifest`) is versioned.
Example: `manifest_version: "3.0"`

## Compatibility Scenarios

**Can an old plugin still run?**
Yes. Backward compatibility is a core mandate of VIREON to protect vendor investments in proprietary plugins.

**Example Evolution:**
```text
Plugin SDK v1  (Synchronous function calls)
      ↓
Provider SDK v2 (Asynchronous Pub/Sub over EventBus)
      ↓
Capability Manifest v3 (Zero-trust granular proxying)
```

**Execution Pipeline for Legacy Plugins:**
If a user loads a plugin compiled against `SDK v1`:
1. The `PluginRegistry` reads the manifest and identifies `version: "v1"`.
2. The runtime injects an **SDK Adapter Proxy**.
3. The Proxy wraps the modern `v3` asynchronous `EventBus` into the synchronous, blocking interface expected by the `v1` plugin.
4. The plugin executes successfully.

## Deprecation Schedule
- **Interfaces**: An SDK version is only fully removed after being deprecated for **two full MAJOR versions** of the Core Runtime.
- **Warnings**: Using deprecated SDKs triggers warnings at runtime but does not fail the execution.

## Forward Compatibility
Plugins must ignore unknown payload fields in `EventBus` messages to maintain forward compatibility. If a `v2` physics engine publishes new fields in its event payload, a `v1` decoder must not crash when parsing it.
