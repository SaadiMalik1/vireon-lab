# VIREON Lab

**VIREON Lab** is the official educational platform and reference implementation for the VIREON ecosystem. It provides interactive tools, Streamlit dashboards, and pre-packaged attack scenarios to help researchers and students understand neuro-security validation.

## Features
- **Interactive Dashboard**: A Streamlit application for real-time visualization of attacks, telemetry, and threat intelligence.
- **Example Providers**: Reference implementations of clinical algorithms (e.g. `NeuroIPS`) and protocols (e.g. `BLELinkGuard`) built on the `vireon.sdk`.
- **Attack Scenarios**: Pre-built signal modifiers and threat models for CTFs and labs.

## Running the Dashboard
The dashboard orchestrates the core `vireon` `ReplayEngine` underneath the hood.

```bash
cd vireon_lab/dashboard
streamlit run app.py
```

## Documentation
All canonical framework architecture documentation is hosted in the core [vireon repository](https://github.com/SaadiMalik1/Vireon/tree/main/docs).
