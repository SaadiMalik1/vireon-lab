# Validation: Thermal Tissue Constraints

**Audience**: Academic Researchers, Security Researchers

## Purpose
This document explains how VIREON models the thermal impact of an implant on surrounding biological tissue.

## What is Simulated
When an implant draws excessive power (either through legitimate high-frequency stimulation or via a malicious resource exhaustion attack), heat is generated. VIREON simulates the localized temperature rise in the tissue immediately surrounding the implant casing.

## Equations & Assumptions
VIREON uses a lumped approximation of the Pennes Bioheat Equation:
```python
dT_dt = (w_b_rho_b_c_b * (T_a - T) + Q_m + Q_ext) / rho_c
```
Where:
- `w_b_rho_b_c_b`: Blood perfusion term (40,000 W/m³K)
- `Q_m`: Metabolic heat generation (10,000 W/m³)
- `Q_ext`: External Joule heating from the BCI electrode
- `rho_c`: Tissue volumetric heat capacity (3.6e6 J/m³K)

**Assumptions**:
- **Homogeneous Tissue**: We assume the surrounding tissue has uniform thermal conductivity and heat capacity.
- **Isotropic Radiation**: Heat dissipates equally in all directions.

## Limitations & Out of Scope
- **No Tissue Damage Model**: The simulator generates an alert when temperature exceeds clinical limits, but it does not model necrosis or permanent physiological damage.

## References
For clinically accurate thermal modeling, researchers should export the VIREON power dissipation metrics and run them through finite-element analysis (FEA) software like COMSOL Multiphysics using the Pennes bioheat transfer equation.
