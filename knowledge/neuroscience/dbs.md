# Deep Brain Stimulation (DBS)

## What is it?
Deep Brain Stimulation (DBS) is a neurosurgical procedure involving the implantation of a medical device (an implantable pulse generator or IPG) that sends electrical impulses through implanted electrodes directly to specific targets in the brain. 

## Why does it matter?
DBS is standard clinical therapy for movement disorders (Parkinson's disease, essential tremor) and is increasingly used for psychiatric conditions (OCD, depression). Because these devices actively alter brain function through applied electrical current, they are highly life-critical cyber-physical systems.

## Security considerations
Unlike passive recording systems (e.g., EEG), an active stimulator introduces direct physical hazards. Compromising a DBS implant allows an attacker to alter the amplitude, frequency, or pulse width of the stimulation.

## Common vulnerabilities
- **Over-stimulation**: Intentionally draining the battery (Denial of Service) or pushing unsafe electrical limits that cause localized tissue heating.
- **Therapy Denial**: Disabling the stimulator, causing immediate physical relapse for a patient reliant on continuous therapy.
- **Firmware Rollback**: Downgrading the IPG's firmware via an insecure OTA (Over-The-Air) update to an older, vulnerable state.

## Relevant standards
- **ISO 14971**: Medical devices - Application of risk management (specifically physical harms mapping).
- **MITRE ATT&CK for ICS**: Techniques such as T0814 (Denial of Service) and T0831 (Manipulation of Control).

## Real devices
- **Medtronic Percept PC**
- **Abbott Infinity DBS**
- **Boston Scientific Vercise**

## Research papers
- *Denning et al., "Neurosecurity: security and privacy for neural devices"* (Tracked in `knowledge/papers/must-read.md`).

## Open-source tools
- **VIREON Runemate DSL**: Experimental framework for constrained therapeutic scripting.

## Where VIREON uses this concept
The **Digital Twin** inside VIREON mathematically models the thermal output and battery drain of a simulated DBS implant. The simulation engine tests whether malicious firmware inputs will violate safe operational bounds before clinical harm occurs.

## Further reading
- [Neurosecurity: Threat Models](../neurosecurity/threat-models.md)
