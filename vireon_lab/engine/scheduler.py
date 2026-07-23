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

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json

@dataclass
class ScheduledEvent:
    timestamp_sec: float
    event_type: str  # "attack", "artifact", "state_transition"
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    executed: bool = False


class EventScheduler:
    """
    Deterministic experiment timeline scheduler.
    Schedules precise timestamped cyber attacks, physiological artifacts, and state transitions
    to produce 100% reproducible neurosecurity benchmarks.
    """
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.timeline: List[ScheduledEvent] = []

    def schedule(self, timestamp_sec: float, event_type: str, name: str, parameters: Optional[Dict[str, Any]] = None):
        """Adds a scheduled event to the benchmark timeline."""
        event = ScheduledEvent(
            timestamp_sec=timestamp_sec,
            event_type=event_type,
            name=name,
            parameters=parameters or {}
        )
        self.timeline.append(event)
        self.timeline.sort(key=lambda e: e.timestamp_sec)

    def get_active_events(self, current_time_sec: float, window_dur_sec: float = 1.0) -> List[ScheduledEvent]:
        """Returns events active within the current time window."""
        active = []
        for e in self.timeline:
            if current_time_sec - window_dur_sec <= e.timestamp_sec <= current_time_sec:
                e.executed = True
                active.append(e)
        return active

    def reset(self):
        """Resets execution status of all timeline events."""
        for e in self.timeline:
            e.executed = False

    def export_metadata(self) -> str:
        """Exports complete benchmark timeline and seed metadata to JSON."""
        return json.dumps({
            "seed": self.seed,
            "total_events": len(self.timeline),
            "timeline": [
                {
                    "timestamp_sec": e.timestamp_sec,
                    "event_type": e.event_type,
                    "name": e.name,
                    "parameters": e.parameters,
                    "executed": e.executed
                }
                for e in self.timeline
            ]
        }, indent=2)
