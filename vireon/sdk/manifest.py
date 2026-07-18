from dataclasses import dataclass, field
from typing import List

@dataclass
class CapabilityManifest:
    name: str
    version: str
    category: str
    publishes_events: List[str] = field(default_factory=list)
    subscribes_events: List[str] = field(default_factory=list)
    mutates_state: List[str] = field(default_factory=list)
    reads_state: List[str] = field(default_factory=list)
    requires_host_access: bool = False
