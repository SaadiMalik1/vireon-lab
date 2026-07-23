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

"""Benchmark test for Asynchronous Simulation Executor throughput."""

import pytest
from vireon_lab.workers import AsyncSimulationExecutor
from knowledge.simulators.closed_loop_simulator import ClosedLoopSystem


def _run_single_sim(seed: int) -> dict:
    sys_inst = ClosedLoopSystem(seed=seed, vulnerable=True, num_cycles=20)
    return sys_inst.run()


def test_async_simulation_executor_throughput():
    """Benchmark mapping multi-session simulations across worker pool."""
    executor = AsyncSimulationExecutor(max_workers=2)
    seeds = [1, 2, 3, 4]
    
    futures = [executor.submit_simulation(_run_single_sim, seed) for seed in seeds]
    results = [f.result(timeout=5.0) for f in futures]

    assert len(results) == 4
    for res in results:
        assert "statistics" in res
    
    executor.shutdown()


@pytest.mark.asyncio
async def test_async_executor_run_async():
    """Verify async await execution using AsyncSimulationExecutor."""
    executor = AsyncSimulationExecutor(max_workers=2)
    res = await executor.run_async(_run_single_sim, 42)
    assert "statistics" in res
    executor.shutdown()
