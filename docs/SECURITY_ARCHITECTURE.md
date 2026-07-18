# Phase 5: Security Architecture Design

## 1. Goal
VIREON must safely execute untrusted, black-box third-party plugins (e.g., vendor proprietary firmware, advanced ML clinical models) without risking the host system, the dataset integrity, or the operation of other plugins. A compromised or malicious plugin must be fully contained.

## 2. Zero-Trust Boundaries
The framework abandons implicit trust. All plugins operate within a Zero-Trust Architecture (ZTA) governed by the `CapabilityEngine`.

### 2.1 Process Isolation (Sandbox)
By default, standard Python plugins run in the same process but are restricted by Capability Proxies. However, **Untrusted** or **Black-Box** plugins must run in isolated boundaries.

- **Level 0 (In-Process Proxy)**: Trusted open-source plugins. Isolated via object capability proxies (`StateStore`, `EventBus`). High performance, weak security against malicious native code.
- **Level 1 (Subprocess IPC)**: Untrusted Python/Native plugins. The Orchestrator spawns a child process. Communication happens purely via gRPC/Protobuf over `stdin/stdout` or local UNIX domain sockets.
- **Level 2 (WASM/Container)**: Vendor black-box binaries (e.g., proprietary DBS firmware). Executed inside a strict WebAssembly sandbox (e.g., `wasmtime`) or lightweight Docker container. No filesystem access, no network access. Only specific capabilities allowed via WASI.

## 3. Inter-Process Communication (IPC)
For Level 1 and Level 2 isolation, VIREON uses a strictly defined IPC contract.
- **Transport**: gRPC or flatbuffers over shared memory (for performance) or local sockets.
- **Format**: All messages must conform to strictly typed Protobuf definitions. No arbitrary Python `pickle` payloads.
- **Verification**: The `EventBus` verifies the capability manifest of the remote sender before forwarding any IPC message to the rest of the system.

## 4. Defending Against Specific Threats

### 4.1 Side-Channel & Timing Attacks
Malicious clinical models may try to infer firmware state by observing precise tick timing.
- **Mitigation**: The Orchestrator enforces a strict, deterministic `sim_clock`. Plugins do not have access to real wall-clock time (`time.time()`). They only receive the synthetic `sim_clock` ticks, neutralizing timing attacks.

### 4.2 Data Exfiltration
Vendor plugins might attempt to steal raw EEG datasets or competitor firmware configurations.
- **Mitigation**: Network access is blocked by default at the container/WASM level. IPC egress is heavily monitored. A plugin can only read EEG data if explicitly granted `clinical.eeg` read capabilities.

### 4.3 Denial of Service (DoS)
A poorly written physics model might enter an infinite loop, halting the simulation.
- **Mitigation**: In Level 1/2 isolation, the Orchestrator enforces watchdog timers on the `on_tick` IPC call. If a plugin exceeds its compute budget (e.g., 50ms per tick), it is forcibly terminated, and a `FaultEvent` is raised.

## 5. Security Engine & Anomaly Detection
The existing `SecurityEngine` (IDS/IPS) is transitioned into a passive monitor plugin. It subscribes to the `EventBus` and monitors IPC traffic for anomalies (e.g., unexpected data types, excessive frequencies).

## 6. Audit Logging
Every capability grant, IPC connection, and capability violation is logged to a write-only, tamper-evident audit log for forensic reproducibility.
