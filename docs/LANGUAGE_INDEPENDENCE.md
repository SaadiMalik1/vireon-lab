# Phase 6: Language Independence Architecture

## 1. Goal
VIREON cannot be a Python-only framework. To attract medical device manufacturers, security researchers, and high-performance physics modelers, the framework must support plugins written in Rust, C, C++, and compiled to WebAssembly (WASM), alongside native Python. Language independence is a core requirement for vendor neutrality and IP protection.

## 2. Universal IPC Contracts
The `PluginRegistry` no longer strictly expects Python class imports. Instead, it expects a **Provider Bundle** that acts as an RPC endpoint. 

### 2.1 The Protobuf Interface definition
All interfaces (`IFirmwareProvider`, `IPhysicsProvider`, etc.), all events (`device.stimulate`), and all state representations (`ClinicalState`) are defined declaratively in Google Protocol Buffers (proto3).

```protobuf
// vireon_provider.proto
syntax = "proto3";
package vireon.sdk;

service ProviderLifecycle {
    rpc Initialize (InitRequest) returns (InitResponse);
    rpc OnTick (TickRequest) returns (TickResponse);
    rpc Shutdown (ShutdownRequest) returns (ShutdownResponse);
}

service EventBus {
    rpc Publish (EventMessage) returns (Ack);
    rpc Subscribe (Topic) returns (stream EventMessage);
}
```

## 3. Supported Languages & Runtimes

### 3.1 Python (Native/In-Process)
For rapid prototyping and ML integration (PyTorch, TensorFlow). Uses direct object-level proxies or in-memory gRPC if isolation is enabled.

### 3.2 Rust (High-Performance/Safe Systems)
For physics engines, thermodynamic models, or secure enclave code. Compiled to native binaries or WASM. Interacts via Tonic (gRPC for Rust).

### 3.3 C/C++ (Legacy Firmware & RTOS Emulation)
Medical device firmware (e.g., FreeRTOS logic, C control loops). Often provided as opaque, pre-compiled shared objects (`.so`/`.dll`) wrapped in a thin gRPC server, or compiled to WASM.

### 3.4 WebAssembly (WASM / WASI)
The ultimate target for untrusted vendor black-boxes. WASM provides a strictly sandboxed, architecture-neutral runtime.
- **WASM Runtime**: VIREON will embed `Wasmtime` or `Wasmer` in the Python Orchestrator.
- **Interface**: Vendor code is compiled to WASM. VIREON calls WASM exported functions corresponding to the `IProvider` lifecycle. Host functions (e.g., `publish_event`) are imported into the WASM module.
- **Benefits**: Perfect isolation, deterministic execution, and the vendor never has to reveal source code.

## 4. Performance Considerations
Passing millions of 30kHz EEG samples per second over gRPC sockets introduces unacceptable latency.
- **High-Throughput Telemetry**: For high-bandwidth continuous data (like raw EEG or ADC channels), plugins will negotiate a **Shared Memory (SHM)** or **Memory-Mapped File (Mmap)** buffer during the `Initialize` phase.
- **Zero-Copy Reads**: Protobuf/gRPC is only used for control-plane signaling (e.g., `START`, `STOP`, `FAULT`). Data-plane reads occur over shared memory using zero-copy formats like Apache Arrow or FlatBuffers.

## 5. Vendor IP Protection
A primary advantage of this architecture is IP protection. A neural implant company can compile their proprietary artifact-rejection algorithm into a WASM blob or stripped Rust binary. They provide this artifact to the FDA or independent researchers using VIREON, without ever exposing their proprietary algorithms to reverse engineering.
