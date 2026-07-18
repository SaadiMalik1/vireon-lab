# Phase 8: Vendor SDK Developer Experience

## 1. Goal
Neurotech vendors (e.g., Neuralink, Medtronic, Synchron) must be able to use VIREON without learning a complex internal architecture. The Vendor SDK provides a frictionless, zero-dependency layer for wrapping proprietary firmware, algorithms, and telemetry decoders into VIREON-compatible plugins.

## 2. Zero-Dependency Principle
Vendors will not install the full `vireon` Python package, which carries heavy dependencies (e.g., PyTorch, MNE-Python). Instead, VIREON provides a lightweight, standalone `vireon-sdk` package. 

```bash
pip install vireon-sdk
```

The SDK only contains the base Interfaces (`IProvider`, `Manifest`), Protobuf definitions, and the IPC client stubs.

## 3. Wrapping C/C++ Firmware
Vendors have existing firmware written in C or C++ for ARM Cortex-M or similar architectures.

### 3.1 The WASM Path (Recommended)
Vendors compile their firmware using a WebAssembly toolchain (e.g., `clang --target=wasm32-wasi`). They link against the VIREON C-SDK headers:

```c
// vendor_firmware.c
#include <vireon_sdk.h>

void on_vireon_tick(uint64_t sim_clock, uint64_t dt) {
    // Run exactly dt microseconds of CPU cycles
    cpu_step(dt);
}

// Export the WASM function
VIREON_EXPORT(on_vireon_tick);
```

### 3.2 The Native Shared Object Path
If the vendor requires native execution or accesses host hardware, they compile their C code into a `.so` (Linux) or `.dll` (Windows) and use the provided VIREON C++ wrapper which handles the gRPC IPC transparently.

## 4. Custom Telemetry Decoders
Vendors use proprietary wireless protocols and packet structures. They must provide a `ProtocolProvider` that implements `decode()`.

```python
from vireon.sdk import IProtocolProvider, Frame, CapabilityManifest

class VendorXDecoder(IProtocolProvider):
    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            name="vendor_x_ble",
            category="protocol",
            publishes=["clinical.eeg"], # Emits decoded EEG
            subscribes=["device.telemetry"] # Listens to raw bytes
        )
        
    def decode(self, raw_bytes: bytes) -> Frame:
        # Vendor proprietary binary parsing
        voltage = struct.unpack("<H", raw_bytes[0:2])[0]
        return Frame(channel=1, voltage=voltage)
```

## 5. Deployment and Discovery
Vendors package their compiled WASM files, Python scripts, and `manifest.yaml` into a `.zip` archive (e.g., `vendor_x_bundle.zip`). 

To run a simulation, researchers simply drop this bundle into the `~/.vireon/plugins/` directory. The VIREON Orchestrator will:
1. Extract the bundle into memory.
2. Parse the `manifest.yaml`.
3. Verify cryptographic signatures.
4. Spawn the isolated runtime (WASM or Python Subprocess) and inject the capability proxies.

## 6. Vendor Simulation Examples
The SDK includes templates for:
- `vireon-sdk-template-c`: A CMake project demonstrating a C firmware wrapper.
- `vireon-sdk-template-rust`: A Cargo project demonstrating a safe Rust physics model.
- `vireon-sdk-template-python`: A Poetry project demonstrating a Python clinical algorithm.
