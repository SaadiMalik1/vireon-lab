# Architectural Boundaries

To ensure the long-term maintainability and vendor neutrality of the VIREON ecosystem, strict boundaries have been defined. Any future feature proposal must be mapped to one of these ownership domains before implementation.

### Runtime Owns
The `vireon.core` and `vireon.engine` modules are the heart of the framework. They own:
- **Lifecycle Management:** Instantiating and orchestrating the simulation loop.
- **Scheduling:** Managing time synchronization (ticks) across all plugins.
- **Registry:** Validating and registering loaded capabilities.
- **Capability Engine:** Authorizing which plugins can access which signals or state elements.
- **Event Bus:** The centralized asynchronous communication hub.
- **State Store:** The deterministic key-value repository replacing the monolithic `DigitalTwin`.

### SDK Owns
The `vireon.sdk` module is the strict interface boundary. It must have zero dependencies on the runtime. It owns:
- **Provider Interfaces:** Contracts like `IVireonPlugin`, `IFirmwareProvider`.
- **Public Types:** Shared data structures like `Event`.
- **Manifests:** The Capability Manifest schema definition.
- **Versioning:** Semantic versioning policies.
- **Compatibility:** Backward compatibility guarantees for external plugins.

### Lab Owns
The `vireon_lab` repository is the educational consumer of the framework. It acts as a set of hosts and tutorials. It owns:
- **Tutorials & Notebooks:** Educational content demonstrating core capabilities.
- **Dashboards:** Educational Streamlit UIs and report generators.
- **Datasets:** Publicly available or synthetic EEG/neuro-data.
- **Educational Providers:** Non-production emulators (e.g., Muse, Emotiv).
- **CTFs & Scenarios:** Gamified attack scenarios (Poisoning, SCA, DoS).
- **Visualizations:** Tooling to explore neuro-data offline.

### Vendors Own
Third-party entities (e.g., Neuralink, Medtronic, academic researchers) building external plugins own:
- **Firmware:** Proprietary or specific device logic.
- **Decoders:** Machine learning models translating neural data.
- **Proprietary Protocols:** BLE, TCP/IP, or custom wireless protocol implementations.
- **Digital Twins:** Detailed biological models for specific therapeutic interventions.
- **Production Plugins:** Mature integrations intended for formal deployment.
