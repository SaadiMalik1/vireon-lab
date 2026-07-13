# ADR 0003: Dual Telemetry Egress (LSL & WebSockets)

## Status
Accepted

## Context
VIREON generates multi-modal telemetry during simulations, consisting of:
1. **Clinical Data**: High-frequency continuous EEG streams.
2. **Diagnostic Data**: Low-frequency discrete metrics (battery level, CPU usage, ZTA trust scores).

We needed a standardized way to emit this data so that external visualization tools, storage backends, and IDS modules could consume it in real-time.

## Decision
We implemented a dual-egress architecture:

1. **Lab Streaming Layer (LSL)**: Chosen for the high-frequency EEG data. LSL is the de facto standard in neuroscience research for time-synchronizing neural time-series data. This allows VIREON to integrate seamlessly with existing BCI software like OpenViBE or EEGLAB.
2. **WebSockets (JSON)**: Chosen for the low-frequency diagnostic state and physical metrics. WebSockets provide an easy integration path for web-based dashboards (like our Streamlit UI) and standard IT infrastructure.

## Consequences

### Positive
- **Interoperability**: VIREON outputs can be consumed by standard neuroscience tools *and* standard IT observability tools.
- **Separation of Concerns**: Clinical researchers can listen exclusively to the LSL streams without parsing JSON diagnostic noise.

### Negative
- **Complexity**: The `Coordinator` must manage two separate network egress streams, increasing the complexity of the shutdown and error-handling logic.
