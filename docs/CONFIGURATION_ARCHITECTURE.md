# Configuration Architecture

## Overview
As VIREON transitions to a modular `IProvider` architecture, configuration management must support decentralized subsystems (Firmware, Battery, Threat Model) without requiring the Core Runtime to understand the schema of those configurations.

## Schema Definition
The configuration architecture is strictly standardized around **YAML** for static definition files, translating to **JSON** during runtime capability resolution and IPC passing.

### Why YAML?
- Excellent support for complex nesting and comments, crucial for neurotechnology researchers defining scenarios.
- Strict mapping to JSON schemas, which aligns perfectly with our JSON-RPC Subprocess IPC layer.

## Configuration Structure

Configuration is divided into two distinct zones:

### 1. Framework Configuration
This configures the `Orchestrator` itself. It is owned entirely by the Runtime.
```yaml
vireon:
  sim_clock_speed: 1.0
  duration_sec: 3600
  security:
    isolation_level: 1
```

### 2. Provider Configuration
This dictates how specific subsystems are initialized. The Runtime parses this section only enough to map it to a specific `Provider` and inject it into their `CapabilityManifest` and `initialize()` method. The Runtime **does not validate** the contents.

```yaml
providers:
  battery_plugin:
    version: "2.1.0"
    config:
      capacity_mah: 500
      leakage_rate: 0.01
  
  proprietary_decoder:
    version: "1.0.0"
    config:
      algorithm: "kalman"
      # The runtime treats this block opaquely and passes it directly to the provider.
```

## Immutability
Once the `ExperimentConfig` is parsed and the `Orchestrator` enters the `RESOLUTION` phase, the configuration becomes **immutable**.
Providers may mutate the `StateStore`, but they cannot alter the fundamental deployment parameters, ensuring reproducibility across benchmark runs.

## Builder API vs Declarative Manifests
While YAML manifests are the primary ingestion format for reproducible science, VIREON also supports a **Builder API** for programmatic generation (e.g., automated hyperparameter searches running in headless Python scripts).

The Builder API strictly validates against the internal JSON Schema before converting into the final immutable configuration object used to boot the Orchestrator.
