# vireon-lab Package Architecture & SDK Reference

This directory contains the core Python package for `vireon-lab`.

## Submodules & Components

- **`vireon_lab.engine`**: High-performance modular signal architecture:
  - **`interfaces`**: Core interfaces (`ISignalGenerator`, `IArtifactInjector`, `IAttackMutator`, `ICircularBuffer`).
  - **`circular_buffer`**: $O(1)$ ring buffer (`CircularBuffer`) for memory-efficient streaming without buffer copying.
  - **`generators`**: Differential neural mass models (`JansenRitNeuralMassGenerator`, `ColoredNoiseARGenerator`).
  - **`artifacts`**: Physiological artifact injectors (`EyeBlinkArtifact`, `EMGBurstArtifact`, `ECGLeakageArtifact`, `ElectrodeMotionArtifact`).
  - **`attacks`**: Threat vector mutators (`GaussianNoiseAttack`, `DCOffsetDriftAttack`, `DoSGroundingAttack`, `SessionReplayAttack`, `DBSPulseOverrideAttack`).
  - **`scheduler`**: Deterministic simulation timeline orchestrator (`EventScheduler`).
- **`vireon_lab.dashboard`**: Interactive Streamlit laboratory dashboard (`app.py`, `live_signal_engine.py`, `forensic_exporter.py`).
- **`vireon_lab.config`**: Centralized configuration management (`LabConfig`).
- **`vireon_lab.auth`**: Telemetry RBAC and cryptographic session token manager (`TelemetrySessionManager`, `Role`, `Permission`).
- **`vireon_lab.middleware`**: Boundary protection middleware (`require_permission`, `TokenBucketRateLimiter`, `handle_exceptions`).
- **`vireon_lab.logging`**: IEC 62304 / FDA compliant structured JSON lines audit logger (`AuditLogger`, `SecurityEventRecord`).
- **`vireon_lab.workers`**: Non-blocking background worker pool for parallel simulations (`AsyncSimulationExecutor`).
- **`vireon_lab.providers`**: Hardware device emulators (OpenBCI Cyton, PiEEG, BLE GATT, DBS LFP).

---

## Developer Usage Examples

### 1. Modular Signal Generation & Threat Mutation
```python
import numpy as np
from vireon_lab.engine.generators.jansen_rit import JansenRitNeuralMassGenerator
from vireon_lab.engine.attacks.mutators import GaussianNoiseAttack
from vireon_lab.engine.circular_buffer import CircularBuffer

# Instantiate generator and ring buffer
gen = JansenRitNeuralMassGenerator(num_channels=8)
buffer = CircularBuffer(num_channels=8, capacity=10000)

# Generate biological cortical signals
signals = gen.generate(num_samples=500, t_start=0.0, sampling_rate=100.0)

# Mutate with threat vector
mutator = GaussianNoiseAttack()
mutated = mutator.mutate(signals, t_axis=np.linspace(0, 5, 500), intensity=1.2)

# Stream into ring buffer
buffer.write(mutated)
window = buffer.read_last(200)
```

### 2. Telemetry RBAC & Audit Logging
```python
from vireon_lab.auth import TelemetrySessionManager, Role, Permission
from vireon_lab.middleware import require_permission, TokenBucketRateLimiter
from vireon_lab.logging import AuditLogger

session_mgr = TelemetrySessionManager()
rate_limiter = TokenBucketRateLimiter(burst_capacity=5)
audit_logger = AuditLogger()

# Issue a clinician token
token = session_mgr.issue_token(Role.CLINICIAN)

@require_permission(Permission.WRITE_THERAPY, session_manager=session_mgr)
def update_dbs_amplitude(amp_ma: float, token_id: str):
    rate_limiter.consume("clinician_client")
    audit_logger.log_event(
        event_type="DBS_PARAM_UPDATE",
        caller_role=Role.CLINICIAN.value,
        action="update_dbs_amplitude",
        parameters={"amp_ma": amp_ma}
    )
    return True
```
