# Brain Regions: The Attack Surface

In traditional cybersecurity, an attack surface comprises network ports, APIs, and user input fields. In neurosecurity, the attack surface is defined by the neuroanatomical regions interfaced with medical hardware. Different regions govern different physiological functions, meaning a successful signal injection attack yields vastly different consequences depending on the target tissue.

## 1. The Motor Cortex (M1)

Located in the frontal lobe along the precentral gyrus, the motor cortex is responsible for planning and executing voluntary movements. 

- **Primary Interface**: Invasive Brain-Computer Interfaces (BCIs) like intracortical microelectrode arrays (e.g., Utah Arrays) are frequently implanted here to restore mobility or communication for paralyzed patients.
- **Threat Vector (Spoofing)**: By injecting synthetic motor intent signals (e.g., mimicking the neural signature for "move mouse left"), an attacker can hijack the patient's digital output, potentially altering text entry, wheelchair navigation, or robotic arm actuation.
- **Threat Vector (Denial of Service)**: Flooding the array with high-amplitude noise prevents the BCI's decoding algorithms from extracting genuine motor intent.

## 2. The Subthalamic Nucleus (STN)

A small, lens-shaped cluster of neurons in the basal ganglia. It is a critical node in the circuitry that regulates movement.

- **Primary Interface**: Deep Brain Stimulation (DBS) for Parkinson's Disease and Essential Tremor.
- **Threat Vector (Over-stimulation)**: The STN operates in a delicate excitatory/inhibitory balance. Maliciously altering the DBS stimulation frequency (e.g., shifting from a therapeutic $130\text{Hz}$ to an aggressive $200\text{Hz}$) can induce severe dyskinesia, rigidity, or rapid exhaustion of neurotransmitters.
- **Threat Vector (Under-stimulation/Suppression)**: Disabling the therapy instantly returns the patient to their baseline pathological state, causing severe tremors or "freezing" of gait.

## 3. The Vagus Nerve

While not technically located inside the brain, the Vagus Nerve (Cranial Nerve X) is the primary parasympathetic conduit connecting the brainstem to the heart, lungs, and digestive tract.

- **Primary Interface**: Vagus Nerve Stimulation (VNS) for drug-resistant epilepsy and severe depression.
- **Threat Vector (Autonomic Disruption)**: Because the vagus nerve directly innervates the sinoatrial node of the heart, an attacker altering VNS pulse width or amplitude risks inducing bradycardia (dangerously slow heart rate) or respiratory distress. This represents a direct, critical threat to life.

## 4. Modeling Regional Constraints in VIREON

When configuring the `DigitalTwin` in the VIREON simulator, the anatomical region dictates the electrochemical safety limits:

1. **Safety Thresholds**: The maximum safe charge density ($\mu C/cm^2$) is much lower in the fragile cortex than it is in peripheral nerves like the Vagus.
2. **Frequency Bounds**: STN DBS operates effectively at high frequencies ($>100\text{Hz}$), whereas VNS operates at much lower frequencies ($20-30\text{Hz}$). 

A core function of our `NeuroethicsGuardrails` is validating that incoming therapeutic requests do not violate the specific biological parameters of the targeted anatomical region.
