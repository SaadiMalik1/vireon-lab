# Neuron Basics: An Engineering Perspective

In neurosecurity, we model the biological neuron not just as a cell, but as an electrochemical circuit component. Understanding this equivalent circuit is essential for designing valid Digital Twins and evaluating how malicious signal injection, impedance spikes, and noise disrupt computation.

## 1. The Equivalent Circuit Model

To simulate a neuron mathematically (e.g., using Hodgkin-Huxley or Leaky Integrate-and-Fire models), we map biological structures to electrical equivalents:

- **Lipid Bilayer (Cell Membrane)** $\rightarrow$ **Capacitor ($C_m$)**: The non-conductive membrane separates extracellular and intracellular fluids (which act as conductive plates), storing charge.
- **Ion Channels** $\rightarrow$ **Variable Resistors/Conductances ($g_x$)**: Transmembrane proteins allow specific ions ($Na^+$, $K^+$, $Cl^-$) to flow when open. Because their permeability changes based on voltage or chemical binding, they act as variable resistors.
- **Concentration Gradients** $\rightarrow$ **Batteries ($E_x$)**: The difference in ion concentrations creates an electromotive force (Nernst potential).
- **Ion Pumps ($Na^+/K^+$ Pump)** $\rightarrow$ **Current Sources**: These actively move ions against their gradients to maintain the battery's charge.

*Relevance to VIREON*: When our `SignalAttackEngine` injects current, it alters the voltage across $C_m$, potentially forcing voltage-gated ion channels to open prematurely.

## 2. The Resting Membrane Potential

A neuron at rest is not electrically neutral. Due to the selective permeability of the membrane and the active work of the $Na^+/K^+$ pump, the inside of the cell is negatively charged relative to the outside.

- **Baseline Voltage**: Typically around **$-70\text{mV}$**.
- **Polarization**: The cell is considered *polarized*. Any injected signal that makes it more positive (e.g., $-50\text{mV}$) is *depolarizing* (excitatory). A signal that makes it more negative (e.g., $-90\text{mV}$) is *hyperpolarizing* (inhibitory).

*Relevance to VIREON*: Deep Brain Stimulation (DBS) often aims to depolarize a target neural population. An attacker suppressing this therapy aims to inject a hyperpolarizing waveform, forcing the neurons back toward their resting state.

## 3. Synaptic Transmission (Information Flow)

Neurons communicate across junctions called synapses. 

- **Chemical Synapses**: The presynaptic neuron releases neurotransmitters that bind to receptors on the postsynaptic neuron. These receptors open ion channels, altering the postsynaptic membrane potential. This is slower, localized, and highly variable.
- **Electrical Synapses (Gap Junctions)**: Direct physical channels connecting the cytoplasm of two neurons, allowing current to flow directly. This is extremely fast and bidirectional.

*Relevance to VIREON*: While neurosecurity hardware (like a BCI or DBS implant) interacts primarily at the macroscopic electrical level (Local Field Potentials), the ultimate threat vector is the disruption of these synaptic network dynamics. Over-stimulation can exhaust neurotransmitter reserves (a form of biological Denial of Service), while precise noise injection can desynchronize population-level firing.

## 4. Modeling the Threat

When developing validation scenarios, remember that the "attacker" is usually constrained by the hardware limitations of the implanted device (e.g., max current amplitude, battery capacity, electrode impedance). 

An attack that assumes the ability to instantly depolarize a neuron beyond the physical limits of the modeled hardware is an invalid threat model. Our goal in VIREON is to strictly enforce these electrochemical and hardware constraints.
