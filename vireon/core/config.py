"""
VIREON Experiment Configuration System.

Loads experiment definitions from TOML files, validates them,
and provides typed access to configuration values. Enables
reproducible experiments by capturing all parameters in a single file.
"""

import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# TOML parsing: use stdlib tomllib (3.11+) or fallback to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


class DeviceConfig(BaseModel):
    """Configuration for the virtual device."""
    type: str = Field(default="synthetic")       # "synthetic", "pieeg", "replay", "cyton", "ganglion", "muse", "emotiv"
    serial_port: str = Field(default="")         # e.g., "/dev/ttyUSB0" or "COM3"
    sample_rate: int = Field(default=250)
    num_channels: int = Field(default=8)


class DatasetConfig(BaseModel):
    """Configuration for data source."""
    path: Optional[str] = Field(default=None)    # Local file path (EDF, CSV, FIF)
    source: Optional[str] = Field(default=None)  # Remote source identifier (e.g., "physionet:chb-mit/chb01")
    loop: bool = Field(default=True)             # Loop dataset when exhausted


class AttackStepConfig(BaseModel):
    """A single scripted attack step within a scenario."""
    time_sec: float = Field(default=0.0)
    attack: str = Field(default="noise")
    duration_sec: float = Field(default=5.0)
    target_channels: List[int] = Field(default_factory=lambda: [0, 1, 2, 3])
    # Attack-specific parameters
    params: Dict[str, Any] = Field(default_factory=dict)


class AttackConfig(BaseModel):
    """Configuration for attacks (simple list or scripted scenario)."""
    active: List[str] = Field(default_factory=list)
    target_channels: List[int] = Field(default_factory=lambda: [1, 3, 5, 7])
    noise_level_uv: float = Field(default=50.0)
    drift_rate_uv_per_sec: float = Field(default=20.0)
    spike_impedance_kohm: float = Field(default=150.0)
    attenuation_factor: float = Field(default=0.05)
    # Scripted scenario steps (if defined, takes precedence over `active`)
    scenario_steps: List[AttackStepConfig] = Field(default_factory=list, alias="scenario")


class SecurityConfig(BaseModel):
    """Configuration for the IDS/IPS security layer."""
    enabled: bool = Field(default=False)
    nsp_enabled: bool = Field(default=False)
    enable_zta: bool = Field(default=False)
    zta_thresholds: dict = Field(default_factory=lambda: {"ota_update": 0.9, "telemetry_read": 0.5})
    rms_high_threshold: float = Field(default=120.0)
    rms_low_threshold: float = Field(default=0.5)
    beta_power_threshold: float = Field(default=35.0)
    max_stimulation_amplitude_ma: float = Field(default=4.0)


class OutputConfig(BaseModel):
    """Configuration for experiment output."""
    report_prefix: str = Field(default="neuroshield_run")
    formats: List[str] = Field(default_factory=lambda: ["json", "html", "md"])
    no_report: bool = Field(default=False)


class StixConfig(BaseModel):
    """Configuration for STIX Threat Intelligence mapping."""
    bundle_path: str = Field(default="plugins/clinical/data/tara_stix.json")
    enabled: bool = Field(default=True)

class WebConfig(BaseModel):
    """Configuration for the web UI."""
    enabled: bool = Field(default=False)
    port: int = Field(default=7777)
    open_browser: bool = Field(default=True)
    lsl_only: bool = Field(default=False)


class EmulationConfig(BaseModel):
    """Configuration for device emulation layers."""
    openbci: bool = Field(default=False)
    ble: bool = Field(default=False)
    ble_attack: str = Field(default="")
    dbs_mode: bool = Field(default=False)
    dbs_attack: str = Field(default="")
    hardware_loopback: bool = Field(default=False)


class PrivacyConfig(BaseModel):
    """Configuration for data anonymization and differential privacy."""
    enabled: bool = Field(default=False)
    epsilon: float = Field(default=1.0)
    anonymize_exports: bool = Field(default=False)


class ExperimentConfig(BaseModel):
    """Complete experiment configuration — the root config object."""
    name: str = Field(default="default")
    seed: Optional[int] = Field(default=None)    # None = non-deterministic
    duration_sec: float = Field(default=10.0)
    interval_sec: float = Field(default=0.1)

    device: DeviceConfig = Field(default_factory=DeviceConfig)
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    attacks: AttackConfig = Field(default_factory=AttackConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    emulation: EmulationConfig = Field(default_factory=EmulationConfig)
    stix: StixConfig = Field(default_factory=StixConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)


def load_config(path: str) -> ExperimentConfig:
    """
    Load an experiment configuration from a TOML file.
    """
    if tomllib is None:
        raise ImportError(
            "No TOML parser available. Install 'tomli' (pip install tomli) "
            "or use Python 3.11+ which includes 'tomllib'."
        )

    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "rb") as f:
        raw = tomllib.load(f)

    # Convert scenario config format correctly
    if "scenario" in raw:
        # Our TOML scenario section is a dict with "steps" array
        # e.g., [scenario] \n [[scenario.steps]]
        if "steps" in raw["scenario"]:
            raw["attacks"] = raw.get("attacks", {})
            raw["attacks"]["scenario_steps"] = []
            for step in raw["scenario"]["steps"]:
                params = {k: v for k, v in step.items() if k not in ("time_sec", "attack", "duration_sec", "target_channels")}
                step_obj = {
                    "time_sec": float(step.get("time_sec", 0.0)),
                    "attack": step.get("attack", "noise"),
                    "duration_sec": float(step.get("duration_sec", 5.0)),
                    "target_channels": step.get("target_channels", [0, 1, 2, 3]),
                    "params": params
                }
                raw["attacks"]["scenario_steps"].append(step_obj)
        del raw["scenario"]
        
    return ExperimentConfig(**raw)


def config_from_cli_args(args) -> ExperimentConfig:
    """
    Build an ExperimentConfig from argparse args (backward compatibility).
    """
    attack_str = getattr(args, "attack", "")
    active_attacks = [a.strip().lower() for a in attack_str.split(",") if a.strip()] if attack_str else []

    board_type = getattr(args, "board", "synthetic")
    num_channels = 8
    if board_type == "muse":
        num_channels = 4
    elif board_type == "emotiv":
        num_channels = 14

    cli_dict = {
        "duration_sec": getattr(args, "duration", 10.0),
        "interval_sec": getattr(args, "interval", 0.1),
        "device": {
            "type": board_type,
            "serial_port": getattr(args, "serial_port", ""),
            "num_channels": num_channels,
        },
        "dataset": {
            "path": getattr(args, "dataset", None),
        },
        "attacks": {
            "active": active_attacks,
            "noise_level_uv": getattr(args, "noise_val", 50.0),
            "drift_rate_uv_per_sec": getattr(args, "drift_val", 20.0),
            "spike_impedance_kohm": getattr(args, "spike_val", 150.0),
            "attenuation_factor": getattr(args, "attenuation_val", 0.05),
        },
        "security": {
            "enabled": getattr(args, "secure_mode", False),
            "nsp_enabled": getattr(args, "nsp", False),
        },
        "output": {
            "report_prefix": getattr(args, "report_prefix", "neuroshield_run"),
            "no_report": getattr(args, "no_report", False),
        },
        "web": {
            "enabled": getattr(args, "web_ui", False),
            "port": 7777,
            "lsl_only": getattr(args, "lsl", False),
        },
        "emulation": {
            "openbci": getattr(args, "emulate_openbci", False),
            "ble": getattr(args, "emulate_ble", False),
            "ble_attack": getattr(args, "ble_attack", ""),
            "dbs_mode": getattr(args, "dbs_mode", False),
            "dbs_attack": getattr(args, "dbs_attack", ""),
            "hardware_loopback": getattr(args, "hardware_loopback", False),
        }
    }

    return ExperimentConfig.model_validate(cli_dict)
