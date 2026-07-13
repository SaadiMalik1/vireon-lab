# NeuroShield Architecture

The NeuroShield platform is composed of distinct modules that interact strictly through defined interfaces. The architecture is designed to prioritize performance, state isolation, and accurate physical emulation, separating the "brain" (the digital twin) from the "nervous system" (the telemetry and coordination layer).

## 1. Digital Twin (`twin.py`)

The `DigitalTwin` is the core state machine of the Virtual Laboratory. It maintains the physical and clinical state of the simulated BCI device.

### Granular Concurrency Model
To support high-frequency simulation (e.g., thousands of channels at 250Hz), the Digital Twin utilizes three distinct, granular `threading.Lock` objects:
- **`hardware_lock`**: Protects low-level physical state variables like `battery_level`, `electrode_impedances`, and `amplifier_saturated`.
- **`clinical_lock`**: Protects high-level diagnostic state, including `clinical_status`, `decoder_confidence`, and `hazard_state`.
- **`therapy_lock`**: Protects stimulation and feedback parameters, such as `stimulation_enabled` and `stimulation_amplitude_ma`.

This granular locking prevents high-frequency battery sag calculations from bottlenecking slower, asynchronous clinical diagnostic updates.

### Physics Engine
The `DigitalTwin` delegates complex thermodynamic and electrical boundary calculations to the `PhysicsEngine`. When the ReplayEngine triggers `set_sim_clock`, the twin automatically simulates:
1. **Battery Sag**: Exponential power draw based on stimulation amplitude and frequency.
2. **Thermal Rise**: Tissue temperature increases modeled off stimulation current.
3. **Brownout Scenarios**: If the battery dips below a safe threshold during an active stimulation pulse, the device enters a simulated brownout state.

## 2. Coordinator (`coordinator.py`)

The `Coordinator` is the orchestration layer that ties the simulation together.

### The ReplayEngine Loop
The core of the simulation is a strict timing loop managed by the `ReplayEngine`. It:
- Pushes synthetic or pre-recorded EEG data into the twin at the defined `sample_rate`.
- Dispatches this data to the `NeuroIDS` for immediate threat analysis.
- Calculates physical constraints and battery usage based on elapsed `dt`.

### Telemetry Dispatch
The `Coordinator` is responsible for broadcasting the internal state of the `DigitalTwin` to external consumers:
- **WebSocket Server (`asyncio`)**: Streams real-time `state`, `eeg`, and `threat` packets to the external clients (like the Streamlit dashboard).
- **Lab Streaming Layer (LSL)**: (Optional) Pushes raw multiplexed signal data to LSL streams for consumption by clinical BCI tools like OpenViBE.

### Configuration
The `ExperimentConfig` is defined using a structured **Pydantic** model (`core/config.py`), replacing loose dict structures, providing robust type validations for physical constants and security thresholds.

## 3. Runemate Compiler Stack (`compiler/`)

NeuroShield incorporates **Runemate**, an embedded Rust-based Domain Specific Language (DSL) used for defining safe, deterministic clinical therapy scripts (e.g., stimulation pulses, UI layout instructions).

The compiler is split into two isolated binaries to prevent untrusted input from crashing the embedded environment:

1. **Forge (The Frontend Compiler)**: 
   - A high-level parser that takes human-readable Runemate scripts (e.g., `SET_AMP 5.0`) and compiles them into a rigid, bounds-checked binary format known as 'Staves'.
   - Validates memory limits and rejects malformed syntax before it reaches the simulation layer.

2. **Scribe (The Embedded Interpreter)**: 
   - Designed for `no_std` environments (simulating an MCU firmware).
   - Safely executes the compiled Staves bytecode inside the virtual environment.
   - Triggers physical changes in the `DigitalTwin` (e.g., increasing `stimulation_amplitude_ma`).

## 4. Web Dashboard (`dashboard/app.py`)

The NeuroShield platform includes an interactive dashboard built with **Streamlit** that pulls live telemetry from the Coordinator's WebSocket stream.

- **Real-Time Visualization**: Renders high-speed EEG traces utilizing Plotly.
- **State Panels**: Displays live `DigitalTwin` physical states (battery, temp, impedance) and alerts.
- **Threat Intel Panel**: Visualizes active detections, **Red Team Engine** feedback scores, and their mapped qTARA classifications. 

The dashboard provides a closed-loop environment where researchers can observe physiological responses, trigger runtime simulated attacks, and analyze the NeuroIDS mitigations interactively.
