# ADR 0002: Tick-Based Physics Simulation Engine

## Status
Accepted

## Context
VIREON must simulate the physiological state of a patient (Digital Twin) and the firmware state of an implant synchronously. Time modeling is critical for cyber-physical simulations. For instance, an attack that drains the battery must be evaluated in parallel with the tissue heating caused by the implant's active stimulation.

We needed to decide how time would advance in the simulation. Options considered were:
1. Continuous time evaluation (pure differential equations integrated over time).
2. Event-driven time (time jumps to the next registered event).
3. Discrete tick-based simulation.

## Decision
We chose a **Discrete Tick-Based Simulation Engine**.

The simulation advances in fixed time steps (ticks), controlled by the `Coordinator`. During each tick:
1. The firmware emulator executes one cycle.
2. The Digital Twin updates its physical state based on the current context (battery drain, temperature flux).
3. The Twin generates a discrete chunk (window) of EEG data corresponding to the time elapsed.

## Consequences

### Positive
- **Determinism**: The simulation is reproducible. A specific random seed and attack configuration will yield the exact same telemetry output on every run.
- **Synchronization**: It guarantees that the firmware, the attack scripts, and the physics model remain perfectly synchronized in time.

### Negative
- **Precision Limits**: Fast transient events (e.g., sub-millisecond electrical spikes) might be aliased or missed if they fall between ticks. The tick resolution must be carefully balanced against computational performance.
