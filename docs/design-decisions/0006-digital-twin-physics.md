# ADR 0006: Centralizing State via Digital Twin Physics Modeling

## Status
Accepted

## Context
Early prototypes of VIREON managed device state (battery percentage, thermal output, execution mode) implicitly within the simulation coordinator or distributed across plugin nodes. When attempting to simulate cascading failure scenarios—such as a malicious firmware update causing high CPU utilization, leading to excessive tissue heating, which subsequently degrades EEG signal impedance—the decentralized state model collapsed. State synchronization became a brittle, timing-dependent issue.

## Decision
We introduced a centralized **Digital Twin** architecture to govern all physical, hardware, and clinical states within the simulation.

1. **Single Source of Truth**: The `DigitalTwin` object acts as the absolute arbiter of reality. If a simulated BLE module consumes power, it queries and updates the central battery model within the twin.
2. **Physiological Coupling**: The Digital Twin explicitly links hardware physics to physiological outcomes. For example, if the twin's thermal model registers >42°C, the twin automatically applies a localized impedance modifier to the outbound EEG signal stream.
3. **Deterministic Progression**: The simulation engine ticks the Digital Twin at fixed intervals, ensuring that physics equations (e.g., thermal dissipation over time) evolve deterministically and reproducibly.

## Consequences

### Positive
- **Emergent Behavior**: Complex attack chains can naturally emerge. An attacker draining the battery via BLE ping floods will eventually cause the Digital Twin to enter a "Low Power Mode," which truncates EEG telemetry without requiring a hardcoded script for that specific interaction.
- **Reproducibility**: Researchers can snapshot and replay the precise physical state of the implant at any tick interval.

### Negative
- **Modeling Complexity**: We are now responsible for approximating complex physics (thermodynamics, lithium-ion discharge curves) and physiology. These approximations must be clearly bounded and caveated to avoid claims of clinical diagnostic accuracy.
- **Performance bottleneck**: All plugins and modules must synchronize through the central Digital Twin, introducing a slight theoretical lock contention under massive concurrency.
