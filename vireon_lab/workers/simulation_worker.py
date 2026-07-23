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

"""Asynchronous Simulation Worker Pool for non-blocking Monte Carlo attack runs."""

import asyncio
import concurrent.futures
from typing import Any, Callable, Dict, List, Optional


class AsyncSimulationExecutor:
    """Non-blocking Background Task Executor using Thread/Process Pool."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def submit_simulation(
        self, target_func: Callable[..., Dict[str, Any]], *args: Any, **kwargs: Any
    ) -> concurrent.futures.Future:
        """Submit a simulation function for background execution."""
        return self._executor.submit(target_func, *args, **kwargs)

    async def run_async(
        self, target_func: Callable[..., Dict[str, Any]], *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:
        """Asynchronously await simulation completion without blocking asyncio loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, lambda: target_func(*args, **kwargs))

    def map_simulations(
        self, target_func: Callable[..., Dict[str, Any]], param_list: List[Tuple[Any, ...]]
    ) -> List[Dict[str, Any]]:
        """Map parameter list across background worker pool."""
        futures = [self._executor.submit(target_func, *p) for p in param_list]
        return [f.result() for f in concurrent.futures.as_completed(futures)]

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown worker pool."""
        self._executor.shutdown(wait=wait)
