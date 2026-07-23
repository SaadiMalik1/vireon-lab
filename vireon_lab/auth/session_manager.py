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

"""Telemetry Role-Based Access Control & Session Token Manager."""

import hmac
import hashlib
import time
import secrets
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Set


class Role(str, Enum):
    """Medical Telemetry User Roles."""
    PATIENT = "PATIENT"
    CLINICIAN = "CLINICIAN"
    MANUFACTURER_TECH = "MANUFACTURER_TECH"
    AUDITOR = "AUDITOR"


class Permission(str, Enum):
    """Medical Device Action Permissions."""
    READ_TELEMETRY = "READ_TELEMETRY"
    WRITE_THERAPY = "WRITE_THERAPY"
    CONFIGURE_CLOSED_LOOP = "CONFIGURE_CLOSED_LOOP"
    UPDATE_FIRMWARE = "UPDATE_FIRMWARE"
    AUDIT_LOGS = "AUDIT_LOGS"


ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.PATIENT: {
        Permission.READ_TELEMETRY,
    },
    Role.CLINICIAN: {
        Permission.READ_TELEMETRY,
        Permission.WRITE_THERAPY,
        Permission.CONFIGURE_CLOSED_LOOP,
        Permission.AUDIT_LOGS,
    },
    Role.MANUFACTURER_TECH: {
        Permission.READ_TELEMETRY,
        Permission.WRITE_THERAPY,
        Permission.CONFIGURE_CLOSED_LOOP,
        Permission.UPDATE_FIRMWARE,
        Permission.AUDIT_LOGS,
    },
    Role.AUDITOR: {
        Permission.READ_TELEMETRY,
        Permission.AUDIT_LOGS,
    },
}


@dataclass
class SessionToken:
    """Cryptographic Telemetry Session Token."""
    token_id: str
    role: Role
    permissions: Set[Permission] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 3600.0)
    signature: str = ""

    def is_valid(self, required_permission: Optional[Permission] = None) -> bool:
        """Check if token is active and possesses required permission."""
        if time.time() > self.expires_at:
            return False
        if required_permission and required_permission not in self.permissions:
            return False
        return True


class TelemetrySessionManager:
    """Manager for issuing and validating telemetry session tokens."""

    def __init__(self, secret_key: Optional[str] = None):
        self._secret_key = secret_key.encode("utf-8") if secret_key else secrets.token_bytes(32)
        self._active_sessions: Dict[str, SessionToken] = {}

    def issue_token(self, role: Role, ttl_seconds: float = 3600.0) -> SessionToken:
        """Issue a signed session token for a given role."""
        token_id = secrets.token_hex(16)
        created_at = time.time()
        expires_at = created_at + ttl_seconds
        perms = ROLE_PERMISSIONS.get(role, set())

        raw_payload = f"{token_id}:{role.value}:{created_at}:{expires_at}".encode("utf-8")
        signature = hmac.new(self._secret_key, raw_payload, hashlib.sha256).hexdigest()

        token = SessionToken(
            token_id=token_id,
            role=role,
            permissions=perms,
            created_at=created_at,
            expires_at=expires_at,
            signature=signature,
        )
        self._active_sessions[token_id] = token
        return token

    def validate_token(
        self, token_id: str, required_permission: Optional[Permission] = None
    ) -> bool:
        """Validate an active session token against expiration and permissions."""
        token = self._active_sessions.get(token_id)
        if not token:
            return False
        
        # Verify HMAC signature integrity
        raw_payload = f"{token.token_id}:{token.role.value}:{token.created_at}:{token.expires_at}".encode("utf-8")
        expected_sig = hmac.new(self._secret_key, raw_payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(token.signature, expected_sig):
            return False

        return token.is_valid(required_permission)

    def revoke_token(self, token_id: str) -> bool:
        """Revoke a session token."""
        if token_id in self._active_sessions:
            del self._active_sessions[token_id]
            return True
        return False
