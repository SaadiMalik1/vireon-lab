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

"""Boundary Middleware for Auth, Rate-Limiting, and Error Handling."""

from vireon_lab.middleware.auth_middleware import require_permission
from vireon_lab.middleware.rate_limiter import TokenBucketRateLimiter
from vireon_lab.middleware.exception_handler import (
    NeurosecurityException,
    AuthorizationError,
    RateLimitExceededError,
    SimulationFaultError,
    handle_exceptions,
)

__all__ = [
    "require_permission",
    "TokenBucketRateLimiter",
    "NeurosecurityException",
    "AuthorizationError",
    "RateLimitExceededError",
    "SimulationFaultError",
    "handle_exceptions",
]
