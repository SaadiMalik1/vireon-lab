# vireon-lab Package Architecture

This directory contains the core Python package for `vireon-lab`.

## Submodules

- **`vireon_lab.config`**: Centralized configuration management (`LabConfig`).
- **`vireon_lab.auth`**: Role-based access control and cryptographic session token manager (`TelemetrySessionManager`, `Role`, `Permission`).
- **`vireon_lab.middleware`**: Boundary protection middleware (`require_permission`, `TokenBucketRateLimiter`, `handle_exceptions`).
- **`vireon_lab.logging`**: IEC 62304 / FDA compliant structured JSON lines audit logger (`AuditLogger`, `SecurityEventRecord`).
- **`vireon_lab.workers`**: Non-blocking background worker pool for parallel simulations (`AsyncSimulationExecutor`).
- **`vireon_lab.dashboard`**: Interactive Streamlit laboratory UI application (`app.py`).
- **`vireon_lab.providers` & `vireon_lab.reference_providers`**: Signal provider abstractions and synthetic datasets.
- **`vireon_lab.scenarios`**: Attack scenarios and vulnerability emulators.
- **`vireon_lab.reports`**: Quality report generation engines.

## Developer Usage Example

```python
from vireon_lab.config import config
from vireon_lab.auth import TelemetrySessionManager, Role, Permission
from vireon_lab.middleware import require_permission, TokenBucketRateLimiter
from vireon_lab.logging import AuditLogger
from vireon_lab.workers import AsyncSimulationExecutor

# Initialize core services
session_mgr = TelemetrySessionManager()
rate_limiter = TokenBucketRateLimiter(burst_capacity=5)
audit_logger = AuditLogger()

# Issue a clinician token
token = session_mgr.issue_token(Role.CLINICIAN)

# Protect handler with permission requirement
@require_permission(Permission.WRITE_THERAPY, session_manager=session_mgr)
def update_therapy_amplitude(amp_ma: float, token_id: str):
    rate_limiter.consume("clinician_client")
    audit_logger.log_event(
        event_type="THERAPY_UPDATE",
        caller_role=Role.CLINICIAN.value,
        action="update_therapy_amplitude",
        parameters={"amp_ma": amp_ma}
    )
    return True
```
