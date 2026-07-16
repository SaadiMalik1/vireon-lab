# Configuration Migration Guide

This guide describes how to migrate your existing simulation configurations (from `config.toml` or dictionary-based configs) to the new strongly-typed `ExperimentConfig` validation schema introduced in recent releases.

## Overview

The `ExperimentConfig` is a Pydantic model located in `vireon.core.config`. It enforces strict typing, boundary checking, and parameter validation.

### Old Approach (Dictionary / Loose TOML)
Previously, configurations were loaded directly via `toml.load` and passed as a generic dictionary:

```python
import toml
from vireon.core.coordinator import Coordinator

config = toml.load("default.toml")
sim = Coordinator(config)
```

### New Approach (Pydantic `ExperimentConfig`)
The configuration must now be validated through the `ExperimentConfig` model. This ensures that parameters like battery capacity, noise thresholds, and physics bounds are mathematically valid *before* the simulation starts.

```python
from vireon.core.config import ExperimentConfig
from vireon.core.coordinator_builder import SimulationBuilder
import toml

raw_config = toml.load("default.toml")
config = ExperimentConfig(**raw_config)

builder = SimulationBuilder()
builder.with_config(config)
```

## Key Parameter Changes

- **`physics.thermal_max`**: Must be explicitly set as a float. Previous loose bounds have been replaced with a strict limit (e.g., 42.0 degrees C).
- **`security.zta_enabled`**: Must be a boolean (defaults to `False` if not present).
- **`telemetry.channels`**: Must be a list of strings defining active LSL channels.

## Troubleshooting

- **Validation Errors**: If the application crashes with a Pydantic `ValidationError` upon startup, check the exact field mentioned in the traceback. The values must now align strictly with the schema definitions.
- **Missing Fields**: Some previously optional fields (like `attack_vector`) may now be required depending on the plugin settings. Set them to `None` or an empty string if unused.
