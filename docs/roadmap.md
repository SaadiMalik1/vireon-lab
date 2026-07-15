# VIREON Roadmap

## Q3 2026: Core Stability
- Stabilize the Rust NeuroDSL integration.
- Implement automated testing for all datasets.
- Refine existing validation benchmarks.

## Q4 2026: Architectural Decoupling
- Refactor the `Coordinator` God class into smaller, isolated services (e.g., `TelemetryService`, `EngineService`).
- Move from standard Python `threading` to `multiprocessing` for true concurrent execution and strict memory isolation.

## Q1 2027: Hardware in the Loop (HIL)
- Full support for Emotiv and Muse boards.
- Expand BLE emulation to cover proprietary Medtronic/Abbott protocols.

## Q2 2027: Advanced Threat Modeling
- Implement physical RF layer simulations (jamming/interference).
- Introduce adversarial machine learning modules for IDS evasion.
