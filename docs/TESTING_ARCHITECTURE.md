# Testing Architecture

## Overview
VIREON's testing architecture is built on the principle that the orchestration runtime and the vendor plugins operate across distinct trust boundaries. Therefore, the testing strategy must account for isolated correctness, integrated routing, and physical simulation fidelity.

The testing story is treated with equal architectural importance as the runtime itself.

## Testing Hierarchy

The testing architecture follows an escalating verification pipeline:

```text
Unit Tests
   ↓
Provider Tests
   ↓
Runtime Tests
   ↓
Integration Tests
   ↓
Simulation Tests
   ↓
Vendor Validation Tests
   ↓
Regression Benchmarks
```

### 1. Unit Tests
* **Target**: Core primitives, math utilities, cryptographic signing, `StateStore` locks.
* **Execution**: Run in isolation without bootstrapping the `Orchestrator` or `EventBus`. Extremely fast execution (< 1ms per test).

### 2. Provider Tests
* **Target**: Individual plugins (e.g., a specific Decoder or Firmware stub).
* **Execution**: The plugin is instantiated with a **Mock Context**. Instead of connecting to the real `Orchestrator`, it connects to an intercepting `MockEventBus`. Tests verify that given a specific input state, the provider publishes the exact expected set of Events.

### 3. Runtime Tests
* **Target**: The `Orchestrator`, `CapabilityEngine`, and `EventBus`.
* **Execution**: Tests deploy dummy plugins with intentionally misconfigured manifests (e.g., trying to write state without permission) to verify that the runtime correctly sandboxes and isolates malicious or broken behavior.

### 4. Integration Tests
* **Target**: Multiple interacting, trusted plugins.
* **Execution**: Assesses end-to-end framework assembly. Ensures that when `Firmware` publishes a `stimulate` event, the `PhysicsProvider` correctly processes it and updates the `StateStore` within the expected timeframe.

### 5. Simulation Tests
* **Target**: Scientific and physiological fidelity.
* **Execution**: Verifies the mathematical outcomes of the physics and neural dynamics engines. Checks that LFP arrays match expected ground truth waveforms given a specific scenario over a multi-minute simulation span.

### 6. Vendor Validation Tests
* **Target**: Proprietary, third-party `SubprocessProviders`.
* **Execution**: Black-box testing. The framework runs a standard test suite against a closed-source vendor binary using standard JSON-RPC inputs to verify compliance with the `IProvider` specification.

### 7. Regression Benchmarks
* **Target**: System-wide performance.
* **Execution**: Automated benchmarks tracking the overhead of the `EventBus` and IPC mechanisms. If event routing latency increases by more than 5%, CI automatically blocks the PR.
