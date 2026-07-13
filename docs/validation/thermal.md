# Validation: Thermal Tissue Constraints

**Audience**: Academic Researchers, Security Researchers

## Purpose
This document explains how VIREON models the thermal impact of an implant on surrounding biological tissue.

## What is Simulated
When an implant draws excessive power (either through legitimate high-frequency stimulation or via a malicious resource exhaustion attack), heat is generated. VIREON simulates the localized temperature rise in the tissue immediately surrounding the implant casing.

## Equations & Assumptions
VIREON uses a highly simplified thermodynamic approximation:
```python
Delta_Temperature = (Power_Dissipated * Thermal_Resistance) - (Cooling_Rate * Time)
```

**Assumptions**:
- **Homogeneous Tissue**: We assume the surrounding tissue has uniform thermal conductivity and heat capacity.
- **Static Blood Flow**: We do not model the body's thermoregulatory response (e.g., increased localized blood flow to cool the tissue).
- **Isotropic Radiation**: Heat dissipates equally in all directions from a spherical point source.

## Limitations & Out of Scope
- **Not Medically Validated**: The specific heat capacity values used in the code are placeholder constants. They do not accurately reflect gray matter, white matter, or cerebrospinal fluid.
- **No Tissue Damage Model**: The simulator generates an alert when temperature exceeds 39°C, but it does not model necrosis or permanent physiological damage.

## References
For clinically accurate thermal modeling, researchers should export the VIREON power dissipation metrics and run them through finite-element analysis (FEA) software like COMSOL Multiphysics using the Pennes bioheat transfer equation.
