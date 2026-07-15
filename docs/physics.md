# Physics Boundary Conditions and Limits

VIREON implements realistic physics simulations for hardware emulation. These physics models have strict boundary conditions to maintain stability and biological fidelity.

## 1. Bioheat Modeling (Thermal Dynamics)
- **Model**: Pennes Bioheat Transfer Equation.
- **Integrator**: Runge-Kutta 4th Order (RK4).
- **Bounds**:
  - Baseline tissue temperature: `37.0 °C`.
  - Minimum allowed temperature: `35.0 °C`.
  - Maximum critical shutdown: `43.0 °C` (configurable via IPS threshold).
  - Blood perfusion and metabolic heat generation are bounded to human-realistic values to prevent runaway thermal explosion during high-frequency integration.

## 2. Battery Dynamics
- **Model**: Open-Circuit Voltage (OCV) with dynamic Internal Resistance.
- **Bounds**:
  - State of Charge (SoC): Strictly bounded between `0.0` (0%) and `1.0` (100%).
  - Cutoff Voltage: Minimum operation voltage (e.g., 3.2V for standard Li-Ion) below which the device safely shuts down.
  - Internal resistance dynamically scales with depletion but is clamped to realistic limits to prevent divide-by-zero singularities.

## 3. Neural Integration (Kuramoto Dynamics)
- **Model**: Sub-stepped Kuramoto Oscillators.
- **Bounds**:
  - To track biological variance perfectly and avoid numerical instability during low-frequency replay ticks, the simulator utilizes adaptive `dt` sub-stepping.
  - Sub-step condition: `dt_sub <= 1 / (10 * max_freq)` where `max_freq` is the maximum dominant frequency of the neural oscillators.
  - Coupling strength $K$ is strictly bounded to prevent immediate unphysical global synchronization.

## 4. Impedance Models
- **Model**: Dynamic Contact Impedance.
- **Bounds**:
  - Nominal range: `1000 Ω` to `5000 Ω`.
  - Alert threshold: `> 10000 Ω` (typically triggers a lead-off alert in IPS).
  - Absolute minimum: Clamped at `1 Ω` to prevent mathematical overflow in current/power dissipation formulas.
