# Benchmarks: Telemetry Throughput

**Audience**: Systems Engineers, Data Scientists

## Purpose
This document bounds the expected throughput capabilities of VIREON's dual telemetry egress strategy (LSL and WebSockets).

## Benchmark Configuration
- **Network**: Localhost loopback interface (127.0.0.1)
- **Data Shape**: 8-channel EEG at 250 Hz, emitted in chunks

## Results

> [!WARNING]
> **Lack of Statistical Rigor**: The metrics reported below are point-in-time estimates gathered on developer machines. They lack standard deviations, formal hardware specifications, and are not strictly reproduced in automated CI.

### Lab Streaming Layer (LSL)
LSL is highly optimized for multi-channel time-series data.
- **Max Throughput Achieved**: `> 100,000 samples/second` (synthetic stress test)
- **Standard Operation**: VIREON operates well below this limit. The primary constraint is not the network stack, but the simulation loop's ability to generate the procedural EEG data.
- **Latency**: Sub-millisecond jitter over local loopback.

### WebSockets (JSON)
The WebSocket stream emits verbose diagnostic JSON (battery level, CPU usage, ZTA scores).
- **Max Throughput Achieved**: `~5,000 messages/second`
- **Standard Operation**: WebSockets are throttled to emit diagnostic state only when significant state changes occur (e.g., attack injected, trust degraded) or at a steady 1 Hz heartbeat.
- **Latency**: `2ms - 5ms` over local loopback due to JSON serialization overhead.

## Recommendations
Do not attempt to stream raw, high-frequency EEG data over the WebSocket connection. Always use the LSL stream for clinical data capture and analysis, reserving the WebSocket feed strictly for dashboard visualization and diagnostic alerts.
