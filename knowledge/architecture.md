# vireon-lab Architecture & System Reference

`vireon-lab` is an interactive educational platform and security research laboratory built for medical neurotechnology, brain-computer interfaces (BCIs), and closed-loop neurostimulators.

---

## 1. System Architecture Overview

```
                      +---------------------------------------+
                      |         Streamlit Dashboard           |
                      |     (vireon_lab/dashboard/app.py)     |
                      +-------------------+-------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                            Boundary Middleware Layer                              |
|   +--------------------------+  +----------------------+  +--------------------+  |
|   | RequirePermission Auth   |  | TokenBucket Rate     |  | ExceptionHandler   |  |
|   | (auth_middleware.py)     |  | Limiter              |  | (exception_        |  |
|   |                          |  | (rate_limiter.py)    |  |  handler.py)       |  |
|   +--------------------------+  +----------------------+  +--------------------+  |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                              Core Platform Infrastructure                         |
|   +--------------------------+  +----------------------+  +--------------------+  |
|   | Telemetry RBAC & Auth    |  | Centralized Config   |  | Audit Logging      |  |
|   | (vireon_lab/auth/)       |  | (vireon_lab/config)  |  | (vireon_lab/       |  |
|   |                          |  |                      |  |  logging/)         |  |
|   +--------------------------+  +----------------------+  +--------------------+  |
|   +----------------------------------------------------------------------------+  |
|   | Async Simulation Worker Pool (vireon_lab/workers/)                         |  |
|   +----------------------------------------------------------------------------+  |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        Emulators & Simulators Engine                              |
|   +-------------------+  +------------------+  +------------------------------+   |
|   | OpenBCI / PiEEG   |  | BLE / MICS GATT  |  | Closed-Loop DBS System       |   |
|   | Emulators         |  | Stack            |  | Simulator & Attack Detectors |   |
|   +-------------------+  +------------------+  +------------------------------+   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Infrastructure Components

### 2.1 Configuration Management (`vireon_lab/config.py`, `.env.example`)
Centralized environment configuration loaded at runtime. Supported environment parameters:

| Environment Variable | Type | Default | Description |
|----------------------|------|---------|-------------|
| `VIREON_LAB_ENV` | `str` | `"development"` | Execution environment (`development`, `production`, `test`) |
| `VIREON_LAB_PORT` | `int` | `8501` | Dashboard server port |
| `VIREON_LAB_HOST` | `str` | `"127.0.0.1"` | Host binding address |
| `LOG_LEVEL` | `str` | `"INFO"` | System logger verbosity level |
| `LOG_FILE` | `str` | `"logs/vireon_lab_audit.jsonl"` | Target path for JSON audit logs |
| `SIMULATION_SEED` | `int` | `42` | Random seed for simulation reproducibility |
| `DEFAULT_SAMPLING_RATE_HZ` | `float` | `250.0` | Default signal sampling rate |
| `RATE_LIMIT_BURST` | `int` | `5` | Token bucket maximum burst capacity |
| `RATE_LIMIT_REFILL_RATE` | `float` | `1.0` | Tokens refilled per second |

---

### 2.2 Telemetry Role-Based Access Control (RBAC) (`vireon_lab/auth/`)
Implements role-scoped cryptographic session tokens conforming to medical device cybersecurity access controls.

#### Supported Roles & Permission Scopes
- **`PATIENT`**: `READ_TELEMETRY`
- **`CLINICIAN`**: `READ_TELEMETRY`, `WRITE_THERAPY`, `CONFIGURE_CLOSED_LOOP`, `AUDIT_LOGS`
- **`MANUFACTURER_TECH`**: `READ_TELEMETRY`, `WRITE_THERAPY`, `CONFIGURE_CLOSED_LOOP`, `UPDATE_FIRMWARE`, `AUDIT_LOGS`
- **`AUDITOR`**: `READ_TELEMETRY`, `AUDIT_LOGS`

#### Usage Example
```python
from vireon_lab.auth import TelemetrySessionManager, Role, Permission

session_mgr = TelemetrySessionManager()
token = session_mgr.issue_token(Role.CLINICIAN, ttl_seconds=3600.0)

# Validate token
is_valid = session_mgr.validate_token(token.token_id, required_permission=Permission.WRITE_THERAPY)
```

---

### 2.3 Boundary Protection & Middleware (`vireon_lab/middleware/`)

1. **Authentication Decorator (`auth_middleware.py`)**: Enforces permission validation on target telemetry functions.
   ```python
   @require_permission(Permission.CONFIGURE_CLOSED_LOOP, session_manager=session_mgr)
   def set_kp(new_kp: float, token_id: str):
       ...
   ```

2. **Token-Bucket Rate Limiter (`rate_limiter.py`)**: Throttles rapid command bursts to prevent DoS flooding on emulated devices.

3. **Exception Handler (`exception_handler.py`)**: Custom error hierarchy (`NeurosecurityException`, `AuthorizationError`, `RateLimitExceededError`, `SimulationFaultError`) with structured JSON error responses.

---

### 2.4 Structured Audit Logging Engine (`vireon_lab/logging/`)
Complies with **IEC 62304** and **FDA Medical Device Cybersecurity Guidance** for event logging. Emits structured JSON lines format.

#### Record Schema
```json
{
  "timestamp": "2026-07-23T15:00:00.000000+00:00",
  "event_type": "PARAMETER_UPDATE",
  "caller_role": "CLINICIAN",
  "action": "update_closed_loop_params",
  "parameters": {"kp": 0.08},
  "status": "SUCCESS",
  "details": "PID proportional gain adjusted",
  "clinical_risk_score": 0.0
}
```

---

### 2.5 Asynchronous Simulation Worker Pool (`vireon_lab/workers/`)
Non-blocking background thread/process executor allowing long multi-cycle Monte Carlo simulations to run in parallel without locking UI or event loops.

```python
from vireon_lab.workers import AsyncSimulationExecutor

executor = AsyncSimulationExecutor(max_workers=4)
future = executor.submit_simulation(run_dbs_simulation, seed=42)
result = future.result(timeout=5.0)
```

---

## 3. Tiered Testing & Verification

The testing hierarchy is divided into 3 distinct tiers under `tests/`:

1. **Unit Tests (`tests/unit/`)**: Isolated tests for emulators (OpenBCI, PiEEG, BLE, DBS), signal readers (EDF, FIF, EEG), and clinical risk estimators.
2. **Integration Tests (`tests/integration/`)**: End-to-end multi-component tests:
   - `test_closed_loop_attack_integration.py`: Signal generator $\rightarrow$ Closed-Loop System $\rightarrow$ Attack Detector.
   - `test_telemetry_auth_rate_limit_integration.py`: RBAC authentication $\rightarrow$ Rate limiter $\rightarrow$ JSON Audit Logging.
3. **Benchmarks (`tests/benchmarks/`)**:
   - `test_simulation_worker_benchmarks.py`: Asynchronous simulation throughput and worker pool scaling.

Run all tests:
```bash
.venv/bin/pytest
```
