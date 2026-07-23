# Lab 002: STRIDE Threat Modeling for Neural Interface Systems

> **Lab ID:** NL-001-LAB002
> **Track:** Security
> **Difficulty:** Intermediate-Advanced
> **Estimated Time:** 3-4 hours
> **Prerequisites:** NL-001 Lesson (Sections 9-15), understanding of STRIDE methodology
> **Required Software:** None (text-based exercise)
> **Required Hardware:** None

---

## Learning Objectives

By completing this lab you will be able to:

1. Identify trust boundaries in a neurotechnology system
2. Apply the STRIDE threat modeling methodology to a neural interface
3. Construct a structured threat model with documented threats, impacts, and mitigations
4. Prioritize threats using a risk scoring framework
5. Produce a threat model document suitable for a VIREON security assessment

---

## Background

Threat modeling is the systematic identification and evaluation of threats to a system. In neurotechnology, threat modeling is essential because the consequences of a security failure include not just data breach (as in conventional IT) but direct patient harm. STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) is the threat modeling framework most commonly used in the medical device domain.

VIREON requires a structured threat model as the first artifact in any security assessment. This template provides the format that VIREON's validation framework expects.

---

## Exercise: Threat Model a Closed-Loop DBS System

### System Under Analysis

You are performing a security assessment of a **closed-loop deep brain stimulation (DBS) system** with the following specifications:

- **Implantable Pulse Generator (IPG):** Implanted in the chest wall, contains MCU (ARM Cortex-M4, 1 MB flash, 256 KB SRAM), AFE, RF telemetry (MICS band 402-405 MHz), rechargeable battery
- **Lead:** 8-contact lead implanted in the subthalamic nucleus (STN)
- **Programmer:** Clinical tablet with USB-connected programmer wand (MICS antenna)
- **Telemetry protocol:** Proprietary, AES-128-CMAC authentication, AES-128-CCM encryption, 64-bit nonce for replay protection
- **Closed-loop algorithm:** Senses LFP from contacts 0-3, computes beta-band (13-30 Hz) power, adjusts stimulation on contacts 4-7 based on beta power threshold
- **Stimulation parameters:** 0-10 mA, 130-185 Hz, 60-450 us pulse width (these are the safety monitor hard limits)
- **Home monitoring:** Patient has a home monitor that connects via BLE to the IPG nightly and uploads therapy data to a cloud server
- **Clinician web portal:** Clinicians can view patient therapy data and adjust stimulation parameters remotely (commands are queued and delivered during the next in-clinic programming session)

### Your Task

Complete the threat model template below. For each STRIDE category, identify at least two threats specific to this system. For each threat, provide:
- A unique threat ID
- A clear threat description
- The affected component(s)
- The trust boundary where the threat occurs
- Pre-conditions required for the threat
- The attack vector
- The clinical impact
- The likelihood (Low/Medium/High) with justification
- The impact severity (Low/Medium/High/Critical) with justification
- Existing mitigations (if any)
- Proposed additional mitigations
- VIREON validation approach

---

## Threat Model Template

### System Overview

**System Name:** [Fill in]
**System Version:** [Fill in]
**Assessment Date:** [Fill in]
**Assessor:** [Fill in]

### Trust Boundary Diagram

Draw or describe the trust boundaries in this system. At minimum, identify:

1. TB-1: Implant body (IPG + lead) to wireless link
2. TB-2: Wireless link to programmer wand
3. TB-3: Programmer wand to clinical tablet
4. TB-4: Clinical tablet to hospital network
5. TB-5: Hospital network to cloud server
6. TB-6: IPG BLE to home monitor
7. TB-7: Home monitor to cloud server
8. TB-8: Cloud server to clinician web portal
9. TB-9: Clinician to clinician web portal (authentication)

For each trust boundary, specify:
- Data that crosses the boundary
- Security mechanisms at the boundary
- Assumptions about trust on each side

```
+-------------------+     +-------------------+     +-------------------+
|                   | TB1 |                   | TB2 |                   |
|   IPG + Lead      |---->|   MICS Wireless    |---->|   Programmer      |
|   (Trusted)       |     |   Link (Untrusted) |     |   Wand (Trusted)  |
|                   |     |                   |     |                   |
+-------------------+     +-------------------+     +-------------------+
                                                            | TB3
                                                            v
                         +-------------------+     +-------------------+
                         |                   | TB5 |                   |
                         |   Hospital        |<----|   Clinical        |
                         |   Network         | TB4 |   Tablet          |
                         |   (Semi-trusted)  |     |   (Trusted)       |
                         +-------------------+     +-------------------+
                              |                              |
                              v                              |
                         +-------------------+               |
                         |                   |               |
                         |   Cloud Server    |<--------------+
                         |   (Partially      |
                         |    trusted)       |
                         +-------------------+
                              |
                              v TB8
                         +-------------------+
                         |   Clinician Web   |
                         |   Portal          |
                         +-------------------+

+-------------------+     +-------------------+
|                   | TB6 |                   |
|   IPG (BLE)       |---->|   Home Monitor    |
|                   |     |   (Semi-trusted)  |
+-------------------+     +-------------------+
                               |
                               v TB7
                         +-------------------+
                         |   Cloud Server    |
                         +-------------------+
```

### STRIDE Analysis

#### S — Spoofing

| Threat ID | Description | Component | Trust Boundary | Pre-conditions | Attack Vector | Clinical Impact | Likelihood | Impact | Existing Mitigations | Proposed Mitigations | VIREON Validation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S-001 | [Fill in] | | | | | | | | | | |
| S-002 | [Fill in] | | | | | | | | | | |

*Guidance: Spoofing threats involve impersonation. In a neural implant context, who can pretend to be someone or something they are not? Consider: programmer impersonation, implant impersonation, clinician impersonation, patient impersonation.*

#### T — Tampering

| Threat ID | Description | Component | Trust Boundary | Pre-conditions | Attack Vector | Clinical Impact | Likelihood | Impact | Existing Mitigations | Proposed Mitigations | VIREON Validation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T-001 | [Fill in] | | | | | | | | | | |
| T-002 | [Fill in] | | | | | | | | | | |
| T-003 | [Fill in] | | | | | | | | | | |

*Guidance: Tampering involves data modification. In a neural implant, what data could be maliciously modified? Consider: LFP data (affects closed-loop), stimulation parameters, firmware, therapy history, patient identifiers.*

#### R — Repudiation

| Threat ID | Description | Component | Trust Boundary | Pre-conditions | Attack Vector | Clinical Impact | Likelihood | Impact | Existing Mitigations | Proposed Mitigations | VIREON Validation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R-001 | [Fill in] | | | | | | | | | | |

*Guidance: Repudiation involves the inability to trace an action to its source. If someone modifies a patient's stimulation parameters, can the system prove who did it? Consider audit log integrity, session tracking, non-repudiation mechanisms.*

#### I — Information Disclosure

| Threat ID | Description | Component | Trust Boundary | Pre-conditions | Attack Vector | Clinical Impact | Likelihood | Impact | Existing Mitigations | Proposed Mitigations | VIREON Validation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| I-001 | [Fill in] | | | | | | | | | | |
| I-002 | [Fill in] | | | | | | | | | | |

*Guidance: Information disclosure involves unauthorized data access. What sensitive data flows through this system? Consider: LFP recordings (neural data), stimulation parameters (therapeutic data), device identifiers, patient demographics, firmware version (useful for targeting specific attacks).*

#### D — Denial of Service

| Threat ID | Description | Component | Trust Boundary | Pre-conditions | Attack Vector | Clinical Impact | Likelihood | Impact | Existing Mitigations | Proposed Mitigations | VIREON Validation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D-001 | [Fill in] | | | | | | | | | | |
| D-002 | [Fill in] | | | | | | | | | | |

*Guidance: Denial of service involves making the system unavailable. For a neural implant, loss of availability means loss of therapy. Consider: battery drain, firmware crash, RF jamming, protocol state machine abuse.*

#### E — Elevation of Privilege

| Threat ID | Description | Component | Trust Boundary | Pre-conditions | Attack Vector | Clinical Impact | Likelihood | Impact | Existing Mitigations | Proposed Mitigations | VIREON Validation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E-001 | [Fill in] | | | | | | | | | | |
| E-002 | [Fill in] | | | | | | | | | | |

*Guidance: Elevation of privilege involves gaining unauthorized access to protected functionality. In an implant, the highest privilege level is control of the stimulation circuitry. Consider: buffer overflow in telemetry handler, firmware update exploitation, debug interface access.*

---

### Risk Prioritization

After completing the STRIDE analysis, prioritize all identified threats using this scoring framework:

**Risk Score = Likelihood (1-3) x Impact (1-4)**

| Score | Risk Level | Action Required |
|---|---|---|
| 1-2 | Low | Document, monitor |
| 3-4 | Medium | Mitigate in next release |
| 6-8 | High | Mitigate immediately |
| 9-12 | Critical | Stop deployment, mitigate before any further use |

**Likelihood Scale:**
- 1 (Low): Requires physical access to implant + specialized equipment + significant expertise
- 2 (Medium): Requires physical proximity + commercially available SDR + protocol knowledge
- 3 (High): Remotely exploitable with publicly available tools

**Impact Scale:**
- 1 (Low): Information disclosure with no clinical consequence
- 2 (Medium): Therapy disruption requiring non-urgent clinical intervention
- 3 (High): Direct patient harm requiring urgent clinical intervention
- 4 (Critical): Permanent patient harm or death

### Top 5 Threats

After scoring, list the top 5 highest-risk threats with:
1. Threat ID and description
2. Risk score and level
3. Why this threat deserves priority
4. Concrete mitigation recommendation
5. VIREON validation approach

---

## VIREON Integration

This threat model should be stored in the VIREON knowledge base as:

```
vireon-labs/modules/NL-001/threat-models/
    closed-loop-dbs-stride.json
```

The JSON schema should follow VIREON's ThreatModel specification:

```json
{
  "model_id": "NL-001-TM-001",
  "system_name": "Closed-Loop DBS",
  "assessor": "your-name",
  "date": "2026-07-22",
  "trust_boundaries": [
    {
      "id": "TB-1",
      "name": "Implant to Wireless",
      "from": "IPG",
      "to": "MICS Link",
      "data_crossing": ["LFP samples", "stimulation commands", "device status"],
      "security_mechanisms": ["AES-128-CCM", "AES-128-CMAC", "64-bit nonce"],
      "assumptions": ["AES-128 is not broken", "Keys are unique per device", "Nonce never repeats"]
    }
  ],
  "threats": [
    {
      "id": "T-001",
      "stride_category": "Tampering",
      "description": "...",
      "component": "...",
      "trust_boundary": "TB-1",
      "likelihood": 2,
      "impact": 4,
      "risk_score": 8,
      "risk_level": "High",
      "mitigations": [...],
      "vireon_validation": "..."
    }
  ]
}
```

---

## Success Criteria

Your threat model is complete when:

- [ ] All 9 trust boundaries are identified and described
- [ ] At least 2 threats per STRIDE category (minimum 12 total)
- [ ] Each threat has a clear, specific description (not generic)
- [ ] Each threat has a documented clinical impact
- [ ] Each threat has a justified likelihood and impact rating
- [ ] Risk scores are computed and threats are prioritized
- [ ] Top 5 threats have concrete mitigation recommendations
- [ ] Top 5 threats have VIREON validation approaches
- [ ] The threat model is exported in the JSON schema format

## Common Mistakes

1. **Generic threats:** "An attacker hacks the device" is not a useful threat. Specify: what component, what vulnerability, what attack vector, what clinical consequence.

2. **Ignoring the closed-loop:** Many threat models treat the device as open-loop. The closed-loop (LFP sensing drives stimulation) creates unique threats that must be addressed separately.

3. **Over-focusing on encryption:** Encryption is one defense. Threats exist that encryption does not address (replay, DoS, EMI, insider, social engineering).

4. **Ignoring the ecosystem:** The threat model must cover the entire system — implant, programmer, hospital network, cloud, home monitor, clinician portal. An attack on the home monitor can affect the implant.

5. **No clinical grounding:** Every threat should have a clinical consequence. "Data is exposed" is insufficient — what does the data exposure mean for the patient clinically?

## Suggested Follow-up Labs

- **NL-003:** Firmware architecture analysis — evaluate the firmware-level mitigations identified in this threat model
- **NL-004:** Wireless protocol security — evaluate the MICS/BLE protocol mitigations
- **NL-005:** Closed-loop system security — deep-dive on closed-loop specific threats
