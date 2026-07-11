# NeuroShield Comprehensive Research Audit Report

**Date**: July 11, 2026  
**Auditor**: NeuroShield Project Orchestrator Team  
**Scope**: Codebase audit and verification across Security, Architecture, Simulation Physics, and Performance.  

---

## Executive Summary

This research audit presents a rigorous evaluation of the NeuroShield closed-loop brain-computer interface (BCI) and intrusion prevention system (IPS) simulation platform. The audit has identified critical vulnerabilities, architectural flaws, numerical integration issues, and resource management bugs. 

Key findings include:
1. **Critical Security Vulnerabilities**: Trivial CORS bypasses via omitted `Origin` headers, unauthenticated control and compilation REST APIs, and a cryptographic authentication wrapper that acts as "security theater" by completely skipping signature verification.
2. **Architectural & Design Flaws**: A broken `Coordinator` initialization sequence in the Model Context Protocol (MCP) server that causes immediate crashes, Unix-only dependencies that break cross-platform compatibility, and multi-threading race conditions in Bluetooth Low Energy (BLE) packet reconstruction and OpenBCI emulator teardown.
3. **Simulation Physics Instability**: An unstable numerical implementation of thermodynamic tissue heating that causes false-positive failsafe shutdowns under normal simulated step sizes.
4. **Performance Bottlenecks**: Unbounded RAM growth during simulation execution due to uncapped state logging history.

Detailed analysis and structured, step-by-step remediation plans are provided below to guide the development and implementation tracks.

---

## 1. Security & Authentication Findings

### Finding 1.1: Trivial CORS Validation Bypass
* **Location**: `neuroshield/plugins/reports/web_server.py`, lines 63–68 (`_check_cors`)
* **Severity**: High
* **Description**:
  The Cross-Origin Resource Sharing (CORS) check checks the `Origin` header to restrict requests to localhost or 127.0.0.1. However, if the `Origin` header is absent, the check passes silently.
  ```python
  def _check_cors(self) -> bool:
      origin = self.headers.get("Origin")
      if origin and not origin.startswith("http://localhost:") and not origin.startswith("http://127.0.0.1:"):
          self.send_error(403, "Forbidden CORS origin")
          return False
      return True
  ```
* **Impact**:
  Non-browser clients (such as scripts, server-to-server HTTP requests, or command-line utilities like `curl`) do not automatically attach an `Origin` header. An attacker can bypass the CORS origin restrictions by omitting the header or sending requests via raw TCP/cURL.
* **Remediation**:
  Modify `_check_cors()` to enforce a default-deny policy. If `Origin` is missing, deny the request unless it is an explicitly allowed route or access type. Require that the origin match authorized patterns.

### Finding 1.2: Unauthenticated REST Control and Compilation API Endpoints
* **Location**: `neuroshield/plugins/reports/web_server.py`, lines 152–200 (`do_POST` handler)
* **Severity**: Critical
* **Description**:
  The REST API routes `/api/control` and `/api/runemate/compile` do not validate the session-level WebSocket token (`ws_token`) generated during server startup. While the WebSocket server properly uses `ws_token` to authenticate incoming connections, these HTTP POST endpoints lack any authorization checks. Furthermore, the web server binds globally to `0.0.0.0:7777` by default.
* **Impact**:
  Any device on the local network can send HTTP POST requests to change stimulation parameters (amplitude, frequency, safety modes) or invoke the compilation toolchain (potentially executing compiler processes on the host), leading to unauthorized device control or remote host exploitation.
* **Remediation**:
  1. Enforce validation of the `ws_token` (or a dedicated API key) on all POST requests (e.g., via an `Authorization: Bearer <token>` header or query parameter).
  2. Bind the server to `127.0.0.1` by default unless explicitly configured by the user to bind globally.

### Finding 1.3: Cryptographic Authentication Bypass ("Security Theater")
* **Location**: `neuroshield/plugins/devices/nsp_wrapper.py`, lines 42–51 (`decrypt_payload`)
* **Severity**: High
* **Description**:
  The simulated Neural Sensory Protocol (NSP) wrapper encrypts payloads and attaches an AES-256-GCM authentication tag. However, the decryption routine simply checks if the keys `"payload"` and `"auth_tag"` exist and returns the payload without verifying the authenticity of `auth_tag`.
  ```python
  def decrypt_payload(self, nsp_payload: dict) -> dict:
      if self.simulate_latency_ms > 0:
          time.sleep(self.simulate_latency_ms / 1000.0)
          
      if "payload" in nsp_payload and "auth_tag" in nsp_payload:
          return nsp_payload["payload"]
      return nsp_payload
  ```
  Additionally, during encryption, the signature is computed by appending a random salt (`os.urandom(8)`) to the payload:
  ```python
  auth_tag = hashlib.sha256(payload_str + os.urandom(8)).hexdigest()[:32]
  ```
  Since the random salt is discarded and never included in the output dictionary or transmitted, it is mathematically impossible for the decryptor to verify the signature even if it attempted to do so.
* **Impact**:
  Spoofed or tampered payloads can be injected directly into the digital twin since the signature is never validated, rendering the encryption layer useless.
* **Remediation**:
  1. Modify `encrypt_payload` to transmit the salt (or initialization vector / nonce) along with the ciphertext/hash.
  2. Implement proper signature verification in `decrypt_payload` by re-calculating the SHA256 signature using the transmitted salt and comparing it securely (using constant-time comparison) against the received `auth_tag`.

---

## 2. Core Architecture & Design Findings

### Finding 2.1: Broken Coordinator Initialization in MCP Server
* **Location**: `neuroshield/mcp_server.py`, lines 180–189 (`run_simulation`)
* **Severity**: Critical
* **Description**:
  The `run_simulation` tool attempts to instantiate the simulation coordinator using a raw Python dictionary:
  ```python
  coordinator = Coordinator(raw_config)
  coordinator.start_simulation()
  ```
  However, the `Coordinator` constructor in `neuroshield/core/coordinator.py` requires an `ExperimentConfig` object. Additionally, the `Coordinator` class does not define `start_simulation()` or `stop_simulation()`; its actual lifecycle methods are `setup()`, `run()`, and `teardown()`.
* **Impact**:
  Attempting to run a simulation via the MCP server fails immediately with `AttributeError` (as the code tries to access `.emulation` on a dictionary object) and `AttributeError` (due to calling non-existent methods), rendering the MCP simulation tool completely non-functional.
* **Remediation**:
  1. Load/parse the `raw_config` dictionary into a proper `ExperimentConfig` object using Pydantic (e.g., `ExperimentConfig(**raw_config)` or `ExperimentConfig.model_validate(raw_config)`).
  2. Replace `coordinator.start_simulation()` and `coordinator.stop_simulation()` calls with the correct sequence: `coordinator.setup()`, followed by running the simulation loop (`coordinator.run()`), and then `coordinator.teardown()`.

### Finding 2.2: Ethics Validator Bypass (Configuration Attribute Typo)
* **Location**: `neuroshield/core/guardrails.py`, lines 69–71 (`validate_experiment_config`)
* **Severity**: High
* **Description**:
  The `GuardrailValidator` checks physiological safety and bandwidth limits (e.g. G6 limits) by reading `config.telemetry`:
  ```python
  num_channels = getattr(config.telemetry, "num_channels", 8)
  sample_rate = getattr(config.telemetry, "sample_rate", 250)
  resolution_bits = getattr(config.telemetry, "resolution_bits", 24)
  ```
  However, the `ExperimentConfig` Pydantic model contains no `telemetry` field. The device hardware settings are actually defined under the `device` field (e.g., `config.device.num_channels`).
* **Impact**:
  If the config has no telemetry attribute (or is mocked to `None`), the validator defaults to 8 channels, 250 Hz, and 24 bits. An extremely unsafe hardware configuration (e.g. 1000 channels, 50000 Hz, violating the 50 Mbps physiological cap) will evaluate using the default fallbacks and pass validation without throwing a `GuardrailViolation`.
* **Remediation**:
  Update `guardrails.py` to reference `config.device` instead of `config.telemetry` for `num_channels` and `sample_rate`. Add a fallback or property on `DeviceConfig` for `resolution_bits`.

### Finding 2.3: Non-Atomic BLE Packet Reassembly Race Condition
* **Location**: `neuroshield/core/coordinator.py`, lines 534–535
* **Severity**: Medium
* **Description**:
  The coordinator joins and clears BLE client packets concurrently:
  ```python
  reconstructed_bytes = b"".join(self.ble_client.received_packets)
  self.ble_client.received_packets.clear()
  ```
  Since packets are appended to `received_packets` by an asynchronous BLE thread, a packet can arrive after the `join` call but before the `clear` call.
* **Impact**:
  Incoming packets arriving in this narrow timing window will be permanently lost when `clear()` is executed, leading to transmission corruption or command dropouts.
* **Remediation**:
  Wrap the read and clear operations in a thread lock (e.g., using `self.ble_client.lock`), or pop elements atomically from the list.

### Finding 2.4: PTY TOCTOU Race Condition in OpenBCI Emulator
* **Location**: `neuroshield/plugins/devices/openbci_emulator.py`, lines 164–170 (`_write_to_client`)
* **Severity**: Medium
* **Description**:
  The `_write_to_client` method checks `if self.master_fd is not None` and writes to it. Concurrently, the `stop` method closes `master_fd` and nulls it out under a lock. Because `_write_to_client` does not acquire `self.lock` when evaluating and using `self.master_fd`, a Time-of-Check to Time-of-Use (TOCTOU) race condition exists.
* **Impact**:
  If `stop()` closes and clears `master_fd` between the check and the `write` call, the thread raises `OSError` or `TypeError` crashes, leading to simulation crashes during shutdown.
* **Remediation**:
  Acquire the emulator's thread lock `self.lock` inside `_write_to_client` prior to checking and writing, or handle the `OSError`/`TypeError` exceptions gracefully.

### Finding 2.5: Cross-Platform Compatibility Violation (Unconditional Unix Imports)
* **Location**: `neuroshield/plugins/devices/openbci_emulator.py`, lines 2–5
* **Severity**: Medium
* **Description**:
  The emulator imports Unix-specific modules `pty`, `fcntl`, `termios`, and `tty` unconditionally at the top of the file. However, `pyproject.toml` declares `"Operating System :: OS Independent"`.
* **Impact**:
  Running the code on Windows causes an immediate `ImportError` on startup, violating the OS-independent declaration.
* **Remediation**:
  Move these imports inside the `start()` method or wrap them in platform checks (`if os.name != 'nt'`). Disable OpenBCI emulation gracefully on non-Unix platforms.

---

## 3. Simulation Physics Findings

### Finding 3.1: Thermodynamic Numerical Integration Instability
* **Location**: `neuroshield/core/physics.py`, lines 59–60 (`tick` method)
* **Severity**: Medium
* **Description**:
  The physics engine calculates tissue heating using the Forward Euler integration method:
  $$\Delta T = (H - k(T - 37.0)) \Delta t$$
  where $k = 0.05$ and $H$ is the heating rate. The stability criterion for explicit Forward Euler requires the step size to satisfy $\Delta t < \frac{2}{k}$. For $k = 0.05$, the step size must be $\Delta t < 40.0\text{ seconds}$. 
* **Impact**:
  When the simulation advances with a large step size (such as `dt = 100.0` in standard realism tests), the numerical integration becomes unstable. The temperature overshoots the physical steady-state limit ($43.5^\circ\text{C}$ for a $0.325^\circ\text{C/s}$ heating rate) and spikes to a fatal $69.5^\circ\text{C}$ in a single step, triggering false-positive hardware shutdown alerts.
* **Remediation**:
  Sub-step the integration loop within `tick()`. If `dt` exceeds a stability threshold (e.g., $10.0\text{ seconds}$), divide it into smaller intervals (e.g., steps of $1.0\text{ second}$) and iterate the Euler update.

---

## 4. Performance Findings

### Finding 4.1: Unbounded State Log History Growth (Memory Leak)
* **Location**: `neuroshield/core/twin.py`, line 292 (`_log_state_change`)
* **Severity**: Low
* **Description**:
  On every digital twin state mutation, a snapshot of the current state is appended to `self.history`:
  ```python
  self.history.append(state_copy)
  ```
  There is no maximum size limit or rotation mechanism applied to this list.
* **Impact**:
  During long-running simulations, `self.history` will grow indefinitely, consuming an unbounded amount of RAM and eventually leading to out-of-memory crashes.
* **Remediation**:
  Implement a circular buffer or maximum history cap (e.g., keeping only the last 1,000 states), or offload historical states to disk/database.

---

## Verification Evidence & Methodology

The findings in this report were verified through high-fidelity static code analysis of the NeuroShield repository, matching implementation details with security, concurrency, and mathematical modeling principles. 

1. **CORS/Auth**: Confirmed by inspecting `web_server.py` where `_check_cors()` bypasses validation when `Origin` is missing and POST endpoints lack authentication token validation.
2. **Ethics Validator**: Verified in `guardrails.py` where `config.telemetry` is accessed, but `ExperimentConfig` only defines `config.device`.
3. **NSP Cryptography**: Verified in `nsp_wrapper.py` where `decrypt_payload` returns the payload immediately if keys exist, and salt is not sent.
4. **Instability**: Mathematically verified via Euler stability criteria:
   $$|1 - 0.05 \times 100| = |-4| = 4 > 1$$
   This causes divergence/overshoot.
