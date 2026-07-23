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

"""Token-Bucket Rate Limiter to mitigate command flooding and DoS attacks."""

import time
from typing import Dict, Tuple
from vireon_lab.middleware.exception_handler import RateLimitExceededError


class TokenBucketRateLimiter:
    """Thread-safe Token Bucket Rate Limiter per client/source key."""

    def __init__(self, burst_capacity: int = 5, refill_rate_per_sec: float = 1.0):
        self.capacity = float(burst_capacity)
        self.refill_rate = refill_rate_per_sec
        # Maps key -> (tokens, last_update_time)
        self._buckets: Dict[str, Tuple[float, float]] = {}

    def consume(self, key: str, tokens_requested: float = 1.0) -> bool:
        """Consume tokens for a key. Returns True if permitted, raises error if exceeded."""
        now = time.time()
        tokens, last_update = self._buckets.get(key, (self.capacity, now))

        # Refill tokens based on elapsed time
        elapsed = now - last_update
        tokens = min(self.capacity, tokens + elapsed * self.refill_rate)

        if tokens >= tokens_requested:
            tokens -= tokens_requested
            self._buckets[key] = (tokens, now)
            return True
        else:
            self._buckets[key] = (tokens, now)
            raise RateLimitExceededError(
                f"Rate limit exceeded for '{key}'. Tokens remaining: {tokens:.2f}/{self.capacity}"
            )

    def reset(self, key: str) -> None:
        """Reset bucket for a key."""
        if key in self._buckets:
            del self._buckets[key]
