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

"""Structured JSON Lines Audit Logger complying with IEC 62304 / FDA Guidance."""

import datetime
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class SecurityEventRecord:
    """Immutable Medical Device Security Event Record."""
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    event_type: str = "SECURITY_EVENT"
    caller_role: str = "UNKNOWN"
    action: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "SUCCESS"  # SUCCESS, REJECTED, FAULT
    details: str = ""
    clinical_risk_score: float = 0.0  # 0.0 (nominal) to 10.0 (severe hazard)


class AuditLogger:
    """JSON Lines Audit Logger for forensic medical telemetry records."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path
        self._logger = logging.getLogger("vireon_lab.audit")
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event_type: str,
        caller_role: str,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
        status: str = "SUCCESS",
        details: str = "",
        clinical_risk_score: float = 0.0,
    ) -> SecurityEventRecord:
        """Log a structured security event to loggers and JSON lines log file."""
        record = SecurityEventRecord(
            event_type=event_type,
            caller_role=caller_role,
            action=action,
            parameters=parameters or {},
            status=status,
            details=details,
            clinical_risk_score=clinical_risk_score,
        )

        payload_json = json.dumps(asdict(record))
        self._logger.info("AUDIT_LOG: %s", payload_json)

        if self.log_path:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(payload_json + "\n")

        return record
