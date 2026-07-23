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

"""Centralized Configuration Management for vireon-lab."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class LabConfig:
    """System-wide configuration settings for vireon-lab."""

    env: str = os.getenv("VIREON_LAB_ENV", "development")
    host: str = os.getenv("VIREON_LAB_HOST", "127.0.0.1")
    port: int = int(os.getenv("VIREON_LAB_PORT", "8501"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: Optional[Path] = (
        Path(os.getenv("LOG_FILE", "logs/vireon_lab_audit.jsonl"))
        if os.getenv("LOG_FILE") != ""
        else None
    )
    simulation_seed: int = int(os.getenv("SIMULATION_SEED", "42"))
    default_sampling_rate_hz: float = float(os.getenv("DEFAULT_SAMPLING_RATE_HZ", "250.0"))
    default_device_mac: str = os.getenv("DEFAULT_DEVICE_MAC", "AA:BB:CC:DD:EE:FF")
    rate_limit_burst: int = int(os.getenv("RATE_LIMIT_BURST", "5"))
    rate_limit_refill_rate: float = float(os.getenv("RATE_LIMIT_REFILL_RATE", "1.0"))

    @classmethod
    def load(cls) -> "LabConfig":
        """Instantiate configuration from environment variables."""
        return cls()


config = LabConfig.load()
