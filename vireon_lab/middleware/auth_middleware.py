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

"""Authorization Middleware Decorator."""

import functools
from typing import Any, Callable, Optional
from vireon_lab.auth.session_manager import Permission, TelemetrySessionManager
from vireon_lab.middleware.exception_handler import AuthorizationError


def require_permission(
    permission: Permission,
    session_manager: TelemetrySessionManager,
    token_param_name: str = "token_id",
) -> Callable:
    """Decorator to enforce permission validation on telemetry handlers."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            token_id = kwargs.get(token_param_name)
            if not token_id:
                raise AuthorizationError("Missing session token ID")

            if not session_manager.validate_token(token_id, required_permission=permission):
                raise AuthorizationError(
                    f"Session token lacks required permission: {permission.value}"
                )

            return func(*args, **kwargs)
        return wrapper
    return decorator
