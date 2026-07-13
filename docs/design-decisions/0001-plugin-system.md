# ADR 0001: Event-Driven Plugin Architecture

## Status
Accepted

## Context
VIREON is designed to simulate a wide variety of medical implants (e.g., Deep Brain Stimulators, Vagus Nerve Stimulators, Cochlear Implants) and a growing catalog of attack vectors. Initially, adding a new device or attack required modifying the core physics engine and the coordinator loop. This created a monolithic structure where changes to one threat model could unintentionally break the physics simulation of unrelated devices.

## Decision
We implemented a loosely coupled, event-driven Plugin Architecture utilizing a central `EventBus`.

1. **Core Engine Isolation**: The core engine (Digital Twin, Simulation Loop) is completely agnostic to specific attacks or devices.
2. **Plugin Registry**: New modules (Devices, Attacks, Datasets) must inherit from base plugin classes and register themselves at runtime.
3. **Event Bus**: Plugins communicate with the core engine and other plugins exclusively by publishing and subscribing to events (e.g., `EVENT_BATTERY_DRAIN`, `EVENT_ATTACK_INJECTED`).

## Consequences

### Positive
- **Extensibility**: Researchers can model new proprietary hardware or zero-day attacks without needing to fork or modify the core VIREON repository.
- **Stability**: A crashing or poorly written experimental plugin is isolated and less likely to corrupt the core simulation state.

### Negative
- **Latency**: The overhead of serializing and dispatching messages through an event bus introduces slight execution latency compared to direct function calls.
- **Traceability**: Debugging requires tracing event flows rather than reading standard sequential stack traces.
