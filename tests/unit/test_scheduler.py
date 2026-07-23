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

import pytest
import json
from vireon_lab.engine.scheduler import EventScheduler

def test_event_scheduler_timeline():
    scheduler = EventScheduler(seed=42)
    scheduler.schedule(10.0, "attack", "Gaussian Noise", {"intensity": 1.5})
    scheduler.schedule(25.0, "artifact", "EyeBlink", {"amplitude_uv": 150.0})
    
    assert len(scheduler.timeline) == 2
    active = scheduler.get_active_events(current_time_sec=10.5, window_dur_sec=1.0)
    assert len(active) == 1
    assert active[0].name == "Gaussian Noise"

def test_event_scheduler_export_metadata():
    scheduler = EventScheduler(seed=123)
    scheduler.schedule(5.0, "attack", "DoS", {"channel": 0})
    
    meta_json = scheduler.export_metadata()
    parsed = json.loads(meta_json)
    
    assert parsed["seed"] == 123
    assert parsed["total_events"] == 1
    assert parsed["timeline"][0]["name"] == "DoS"
