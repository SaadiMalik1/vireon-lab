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

"""Domain Exceptions and Exception Handling Decorators."""

import functools
import logging
from typing import Any, Callable, Dict


logger = logging.getLogger("vireon_lab.middleware.exception_handler")


class NeurosecurityException(Exception):
    """Base exception for all vireon-lab security domain errors."""
    def __init__(self, message: str, error_code: str = "ERR_GENERAL_SECURITY"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def to_dict(self) -> Dict[str, Any]:
        return {"error": self.message, "code": self.error_code}


class AuthorizationError(NeurosecurityException):
    """Raised when caller fails permission or role authorization."""
    def __init__(self, message: str = "Unauthorized command access"):
        super().__init__(message, error_code="ERR_AUTH_REJECTED")


class RateLimitExceededError(NeurosecurityException):
    """Raised when command throughput exceeds rate-limiting thresholds."""
    def __init__(self, message: str = "Rate limit threshold exceeded"):
        super().__init__(message, error_code="ERR_RATE_LIMIT_EXCEEDED")


class SimulationFaultError(NeurosecurityException):
    """Raised when numerical or signal processing pipeline encounters unrecoverable fault."""
    def __init__(self, message: str = "Simulation processing pipeline fault"):
        super().__init__(message, error_code="ERR_SIMULATION_FAULT")


def handle_exceptions(default_return: Any = None) -> Callable:
    """Decorator to trap NeurosecurityException and wrap into structured dict response."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except NeurosecurityException as e:
                logger.warning("Trapped security exception in %s: %s", func.__name__, e.message)
                return e.to_dict()
            except Exception as e:
                logger.error("Unexpected fault in %s: %s", func.__name__, str(e))
                return {"error": str(e), "code": "ERR_UNEXPECTED_SYSTEM_FAULT"}
        return wrapper
    return decorator
