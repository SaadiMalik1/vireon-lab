# Action Potentials: Thresholds & Trigger Vulnerabilities

Building upon the [Neuron Basics](neuron-basics.md) equivalent circuit model, an action potential is the digital, all-or-nothing propagation of electrical charge down a neuron's axon. In neurosecurity, we view action potentials as the fundamental computational event that we either want to safely induce (via therapy) or protect against malicious induction (via attack).

## 1. The Threshold Potential (The Digital Gate)

The resting membrane potential sits at roughly $-70\text{mV}$. If a depolarizing current is injected—either biologically via synapses or artificially via an electrode—the voltage becomes more positive.

- **The Threshold**: If the voltage reaches approximately **$-55\text{mV}$**, it triggers a massive, rapid opening of voltage-gated $Na^+$ channels.
- **The Spike**: $Na^+$ rushes in, driving the voltage up to $+30\text{mV}$.
- **The Fall**: $Na^+$ channels close, $K^+$ channels open, and the voltage drops back down, often overshooting the resting state (hyperpolarization) before stabilizing.

*Relevance to VIREON*: The threshold acts like a logic gate (an `IF voltage > -55mV THEN FIRE` condition). An attacker injecting noise into an electrode doesn't need to spoof the entire spike; they only need to inject enough current to push the resting potential past the threshold. This makes the system highly sensitive to **sub-threshold accumulation attacks**, where low-amplitude, high-frequency noise forces premature firing.

## 2. Refractory Periods (Hardware Constraints)

Once an action potential fires, the neuron cannot immediately fire again. This is a critical biological rate limit.

- **Absolute Refractory Period**: $Na^+$ channels are locked. No amount of injected current will trigger a spike. 
- **Relative Refractory Period**: The neuron is hyperpolarized (e.g., $-80\text{mV}$). A spike can be triggered, but it requires a significantly larger injected current to reach the $-55\text{mV}$ threshold.

*Relevance to VIREON*: In our `SignalAttackEngine`, if an attacker script attempts to inject high-frequency pulses (e.g., $1000\text{Hz}$) to induce a biological Denial of Service, the digital twin physics engine must enforce these refractory periods. Stimulation applied during the absolute refractory period is "dropped," mimicking packet loss in networking.

## 3. Propagation and Cascading Failures

Action potentials travel down the axon like a wave, triggering the release of neurotransmitters at the synapse, which in turn depolarizes the next neuron in the network.

- **Excitatory Cascades**: If the postsynaptic neuron reaches threshold, it fires, continuing the chain.
- **Inhibitory Dampening**: Some synapses release neurotransmitters that hyperpolarize the target, preventing it from reaching threshold.

*Relevance to VIREON*: A successful signal injection attack on a small, localized group of neurons (such as those adjacent to a Deep Brain Stimulation lead) can cascade through the broader network. This is the physiological mechanism behind stimulation-induced seizures. In the VIREON simulator, evaluating safety means tracking whether a localized injection triggers runaway excitation across the broader connected neural graph.
