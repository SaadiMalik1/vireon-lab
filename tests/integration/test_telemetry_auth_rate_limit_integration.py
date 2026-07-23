# Copyright 2026 VIREON Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Integration test for RBAC session tokens, rate limiter, and JSON audit logging."""

import os
import pytest
from pathlib import Path
from vireon_lab.auth import Permission, Role, TelemetrySessionManager
from vireon_lab.middleware import (
    AuthorizationError,
    RateLimitExceededError,
    TokenBucketRateLimiter,
    require_permission,
)
from vireon_lab.logging import AuditLogger


def test_auth_rate_limit_audit_integration(tmp_path: Path):
    """Test session auth validation, token-bucket throttling, and audit logging."""
    session_mgr = TelemetrySessionManager()
    rate_limiter = TokenBucketRateLimiter(burst_capacity=3, refill_rate_per_sec=0.1)
    audit_file = tmp_path / "audit_test.jsonl"
    audit_logger = AuditLogger(log_path=audit_file)

    # Issue clinician & patient tokens
    clinician_token = session_mgr.issue_token(Role.CLINICIAN)
    patient_token = session_mgr.issue_token(Role.PATIENT)

    @require_permission(Permission.CONFIGURE_CLOSED_LOOP, session_manager=session_mgr)
    def update_closed_loop_params(new_kp: float, token_id: str):
        rate_limiter.consume("cli_client")
        audit_logger.log_event(
            event_type="PARAMETER_UPDATE",
            caller_role=Role.CLINICIAN.value,
            action="update_closed_loop_params",
            parameters={"kp": new_kp},
        )
        return True

    # 1. Clinician can perform parameter update
    res = update_closed_loop_params(new_kp=0.08, token_id=clinician_token.token_id)
    assert res is True

    # 2. Patient token raises AuthorizationError
    with pytest.raises(AuthorizationError):
        update_closed_loop_params(new_kp=0.08, token_id=patient_token.token_id)

    # 3. Burst consumption triggers RateLimitExceededError
    update_closed_loop_params(new_kp=0.09, token_id=clinician_token.token_id)
    update_closed_loop_params(new_kp=0.10, token_id=clinician_token.token_id)
    
    with pytest.raises(RateLimitExceededError):
        update_closed_loop_params(new_kp=0.11, token_id=clinician_token.token_id)

    # 4. Verify audit log file contains recorded events
    assert audit_file.exists()
    lines = audit_file.read_text().strip().split("\n")
    assert len(lines) == 3
