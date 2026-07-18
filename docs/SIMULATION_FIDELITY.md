# Phase 7: Simulation Fidelity Architecture

## 1. Goal
VIREON supports different use cases that require vastly different levels of simulation fidelity. A CI/CD pipeline running thousands of tests might need fast, abstract physics. A regulatory submission for a novel electrode might require slow, cycle-accurate thermodynamics and electrochemistry. VIREON must support running heterogeneous fidelity levels simultaneously without breaking the master simulation loop.

## 2. Layers of Fidelity
All providers that model physical or computational reality (Physics, Clinical, Firmware) must declare their supported Fidelity Level (L0-L3) in their Capability Manifest.

### 2.1 L0: Abstract (Logical)
- **Description**: Instantaneous logic. Ignores physical constraints like propagation delay, battery drain, or thermal load.
- **Example**: `MockEEGReader` providing perfect 250Hz sine waves; a DBS controller that "fires" instantly with 100% efficacy.
- **Speed**: >1000x real-time.

### 2.2 L1: Functional (Approximate)
- **Description**: Approximates physical realities using simple heuristics or statistical models. Includes basic latency and noise.
- **Example**: A firmware emulator running Python logic that adds a 10ms delay to represent Bluetooth transmission time.

### 2.3 L2: Cycle-Accurate / Physics-Accurate
- **Description**: Exact emulation of the hardware or physics.
- **Example**: A QEMU/Renode emulation of an ARM Cortex-M4 CPU executing actual binary firmware, tracking exact clock cycles. Or an FDA-approved Finite Element Analysis (FEA) brain tissue model running on a GPU.
- **Speed**: <1x real-time (slower than reality).

## 3. Fidelity Interoperability
The core challenge is running an L2 Firmware Emulator (cycle-accurate) against an L0 Clinical Model (instantaneous).

### 3.1 The Time-Sync Coordinator
The Orchestrator's `ReplayEngine` acts as the master clock. 
- It maintains `sim_clock` (in microseconds).
- In a mixed-fidelity environment, the clock advances in discrete `dt` steps.
- The Orchestrator uses a **Barrier Synchronization** pattern: It broadcasts `on_tick(sim_clock, dt)` to all providers. The clock *does not advance* until every provider returns a `TickResponse` (ACK).

### 3.2 Time Dilation
Because L2 providers are extremely slow, VIREON operates purely in synthetic simulation time. If a cycle-accurate firmware emulator takes 5 seconds of wall-clock time to compute 1 millisecond of simulation time, the Orchestrator pauses the `sim_clock` until it finishes. This guarantees that fast L0 plugins do not drift ahead of slow L2 plugins.

## 4. Fidelity Degradation (Fallback)
The `ExperimentConfig` allows researchers to specify acceptable fidelity ranges.
If an experiment requests an L2 Physics model but the host machine lacks a GPU, VIREON can automatically fall back to an L1 approximation if the config specifies `allow_fidelity_degradation: true`.

## 5. Reporting Fidelity Constraints
At the end of a simulation, the `ReportGenerator` tags the output dataset with a cryptographic **Fidelity Signature**. This signature proves to auditors (e.g., the FDA) exactly which fidelity level each subsystem operated at during validation, preventing researchers from accidentally submitting L0 abstract simulation data as rigorous L2 physiological validation.
