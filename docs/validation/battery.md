# Validation: Battery Drain Physics

**Audience**: Academic Researchers, Medical Device Engineers

## Purpose
This document outlines the mathematical assumptions, limits, and simplifications used to model battery drain in the VIREON Digital Twin.

## What is Simulated
VIREON simulates a generic lithium-ion primary cell commonly found in Deep Brain Stimulators (DBS). The simulation tracks total capacity (`mAh`) and applies discrete depletion events based on the active state of the implant during each tick.

## Equations & Assumptions
The simulation utilizes a simplified linear depletion model:
```python
Remaining_Capacity = Initial_Capacity - (Active_Draw + Baseline_Draw) * Time_Elapsed
```

**Assumptions**:
- **Constant Voltage**: We assume the battery voltage remains perfectly constant until depletion. In reality, voltage sags non-linearly under heavy load.
- **Perfect Efficiency**: We do not model energy lost to heat during standard operation (except during an explicit thermal attack).
- **Instantaneous State Switching**: The transition from idle to active stimulation draws a flat current instantly, ignoring the capacitor charge-up time typical in actual medical hardware.

## Limitations & Out of Scope
- This model cannot predict exact battery lifespan in a clinical setting.
- We do not model battery chemistry degradation over time (e.g., internal resistance growth).

## References
This simplified model is sufficient for demonstrating **Battery Depletion Attacks** (Denial of Service via continuous stimulation), but should not be used to validate the power budget of a physical implant undergoing FDA approval.
