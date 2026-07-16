# ADR 0010: Security Layer Refactoring and Thread Safety

## Status
Accepted

## Context
During an internal audit of the VIREON simulation engine, several race conditions and thread-safety issues were identified in the `DigitalTwin` and `SignalAttackEngine`. The underlying HTTP dashboard updates and physics simulation loop were concurrently modifying state without proper locks, leading to nondeterministic behavior and theoretical simulation crashes. 

Furthermore, `simulation_context` was exposed globally in `web_server.py`, leaking state across potential parallel test executions or multiple server instantiations.

Additionally, STIX fallback mapping was defaulting to the first available STIX object when a lookup failed, causing false attribution.

## Decision
1. **DigitalTwin Locking**: The `DigitalTwin` class instances now act as the definitive state holder and synchronization point. We introduced `twin._lock` (an `RLock`) which is acquired by `physics.py` during its `tick()` method and by attack modifiers in `attack.py` (e.g., `InsiderThreatAttack`) when updating properties.
2. **Deterministic PRNGs**: Random number generators (`rng`) are explicitly propagated from the engine down to individual attack modifiers in `attack_factory.py`, ensuring reproducibility.
3. **Encapsulated Server State**: The global `simulation_context` and class-level attributes in `BCIAPIRequestHandler` were removed. State is now attached to the `HTTPServer` instance, making the handler purely functional and eliminating global cross-talk.
4. **STIX Attribution Fallback**: Fallback logic in `stix_mapper.py` now explicitly returns `"unclassified"` instead of guessing the first pattern in the dictionary.

## Consequences
- **Positive**: Simulation states are now thread-safe. Multiple GUI dashboards or headless scripts can hit the REST API simultaneously without corrupting the `DigitalTwin` physics state. Tests involving random components are now strictly deterministic.
- **Negative**: Adding locking in the hot path of the `physics.py` `tick()` method introduces slight CPU overhead, but the benefits in safety justify this cost.

## Authors
- Security Refactoring Team
