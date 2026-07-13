# Benchmarks: NeuroIDS Latency

**Audience**: Academic Researchers, Systems Engineers

## Purpose
This document logs the computational latency overhead introduced by the onboard Intrusion Detection System (NeuroIDS) during simulation ticks.

## Benchmark Configuration
- **Hardware**: Standard x86_64 CPU (e.g., Intel Core i7 / AMD Ryzen 7)
- **Engine**: Local CPU execution (No CUDA/GPU acceleration used in this baseline)
- **Simulation Tick Size**: 250 samples at 250 Hz (1.0 second chunks)

## Results

### Deep Autoencoder (PyTorch)
The Deep Autoencoder provides the highest fidelity anomaly detection but incurs significant computational overhead.
- **Inference Latency**: `~45ms - 55ms` per tick.
- **Impact**: This latency breaks hard real-time constraints for closed-loop BCI systems that require sub-10ms response times (e.g., reactive epilepsy suppression).

### Linear Autoencoder (Numpy)
The Linear Autoencoder is the fallback mechanism used when the system enters a degraded trust state or when hardware resources are constrained.
- **Inference Latency**: `< 2ms` per tick.
- **Impact**: Suitable for hard real-time execution, but with lower detection accuracy for complex, non-linear attacks.

## Recommendations
For simulations focusing on **network-level attacks** (BLE flooding), the PyTorch module can be disabled in the `SecurityConfig` to maintain strict timing synchronicity. For simulations focusing on **subtle physiological anomalies** (e.g., state inference), the ~50ms penalty is acceptable as the simulation does not require hard real-time physical actuation.
