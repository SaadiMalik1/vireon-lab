# Phase 5: Threat Model Audit — Vireon Neurosecurity Simulation Platform

**Audit Phase:** 5 of 12  
**Classification:** Threat Model Documentation Assessment  
**Scope:** Asset identification, trust boundary definitions, attack surface analysis, threat actor coverage, STRIDE/MITRE mappings, assumption documentation  
**Source Artifacts:** `threat_models/*.yaml`, `STRIDE.md`, `MITRE.md`, supporting source code  
**Date:** 2025-07-09  

---

## Executive Summary

The Vireon threat model documentation represents a **genuinely strong foundational effort** in medical device security modeling. The four YAML-based device threat models (DBS, VNS, Cochlear, BCI) demonstrate domain expertise, epistemic discipline (avoiding speculative threats), and proper use of structured frameworks. However, the threat models are undermined by stale cross-references, missing severity/risk scoring, incomplete threat actor coverage (particularly supply chain and insider threats), and a thin MITRE mapping that fails to integrate with the YAML models. Most critically, the threat models focus exclusively on *simulated device* threats while largely ignoring threats to the *simulation platform itself*, creating a dangerous blind spot.

**Overall Rating: NEEDS IMPROVEMENT (C+)** — Strong domain modeling with significant structural and coverage gaps.

---

## 1. Asset Identification

**Rating: ACCEPTABLE (B)**

### 1.1 Assets Catalogued

The threat model documentation across `threat_models/*.yaml` identifies the following asset classes:

| Asset Class | Specific Assets | Assessment |
|---|---|---|
| Neural signals | EEG data, Local Field Potentials (LFP) | **Good.** Core data assets for the simulation domain. |
| Stimulation parameters | Pulse width, amplitude, frequency, electrode configuration | **Good.** These are the primary safety-critical parameters. |
| Device firmware | Implant firmware, companion app firmware | **Good.** Correctly identified as both an asset and an attack vector. |
| BLE pairing keys | Long-term keys, session keys, LTK/IRK | **Good.** Wireless security credentials properly identified. |
| Patient clinical data | Diagnosis, stimulation history, clinical outcomes | **Good.** PHI/clinical data recognized. |
| Therapy session state | Active session parameters, real-time feedback | **Good.** Session state is a transient but critical asset. |
| Telemetry data | Device diagnostics, battery status, impedance measurements | **Adequate.** Operational data identified but its sensitivity may be understated. |

### 1.2 Missing Assets

The following assets are present in the codebase but absent from the threat models:

- **MCP server secret key** (`~/.vireon/mcp_secret.key`): A 256-bit secret that authenticates the clinician interface. Its compromise grants full MCP access.
- **WebSocket Bearer token**: The single shared authentication token for all web API clients. Its compromise grants full platform access.
- **NeuroDSL program source code**: User-supplied DSL programs that are compiled and executed by the VM. This is both an asset and an attack vector.
- **Plugin registry state**: The whitelist of permitted plugins — if an attacker can modify this, they can inject arbitrary code via the plugin system.
- **ZTA trust scores and policy configuration**: The zero-trust policy engine's state. Manipulation could elevate trust for untrusted channels.
- **Simulation session data**: Aggregate data across multiple simulated sessions, which could reveal research patterns or vulnerabilities in the simulation itself.

### 1.3 Asset Sensitivity Classification

The threat models do not apply a sensitivity classification (e.g., Confidential / Internal / Public) or a CIA triage (Confidentiality / Integrity / Availability priority) to identified assets. This makes it impossible to prioritize threat mitigation.

---

## 2. Trust Boundary Definitions

**Rating: GOOD (B+)**

### 2.1 Documented Trust Boundaries

The threat models define the following trust boundaries:

| Boundary | Description | Assessment |
|---|---|---|
| Air (wireless) | The wireless interface between implant and external equipment | **Good.** Primary attack surface for medical devices. |
| BLE link | Bluetooth Low Energy connection for short-range communication | **Good.** Properly treated as a distinct trust boundary with specific protocol concerns. |
| Companion app | Mobile application interfacing with the implant | **Good.** Recognized as potentially compromised (untrusted). |
| Cloud backend | Remote server for data storage and therapy management | **Good.** Traditional trust boundary with well-understood threats. |
| Firmware update channel | OTA mechanism for deploying firmware to the implant | **Good.** Correctly identified as high-risk. |
| Clinician interface | Clinical programming and monitoring interface (MCP) | **Good.** Clinician-side trust boundary. |

### 2.2 Attacker Capability Levels

The threat models define attacker capability levels L0 through L6. This graduated scale is **well-structured** and allows for proportionate threat assessment:

- **L0:** Passive observer with no specialized equipment.
- **L1–L2:** Hobbyist with SDR or basic BLE tools.
- **L3–L4:** Resourced attacker with protocol-level knowledge and custom hardware.
- **L5–L6:** Nation-state or well-funded adversary with firmware reverse-engineering capability.

This is a **notable strength** of the threat model documentation. The capability-level framework enables precise threat-to-capability mapping.

### 2.3 Undocumented Trust Boundaries

The following trust boundaries exist in the codebase but are not reflected in the threat models:

- **Web API ↔ Core simulation engine:** The web server directly invokes core simulation functions with no mediation layer. This trust boundary is architecturally absent (as noted in the Phase 4 security engineering review, finding TB-001).
- **MCP ↔ Core simulation engine:** The MCP server explicitly states "trust boundary is undefined" (Phase 4 finding TB-002). The threat models should document this as a *known gap* with associated risk.
- **NeuroDSL compiler ↔ VM:** The compiler and VM are treated as a single trust zone, but the compiler's type truncation vulnerability (Phase 4 finding INVAL-001) demonstrates that the compiler output cannot be fully trusted by the VM.
- **Plugin system ↔ Core engine:** While the plugin whitelist is enforced, the threat models do not document the plugin interface as a trust boundary.
- **Build environment → Runtime:** The poisoned lockfile (Phase 4 finding DEP-001) demonstrates that the build environment is a trust boundary that has been violated.

---

## 3. Attack Surface Analysis

**Rating: GOOD (B)**

### 3.1 Documented Attack Surfaces

The threat models enumerate attack surfaces across multiple vectors:

| Surface | Details | Assessment |
|---|---|---|
| Wireless (BLE, RF) | Signal interception, injection, replay, jamming | **Good.** Comprehensive coverage of wireless threats. |
| Firmware OTA | Man-in-the-middle, downgrade, malicious firmware | **Good.** Correctly identifies firmware update as primary code-injection vector. |
| Companion app | Compromised app, malicious app masquerading as legitimate | **Good.** Treats companion app as potentially hostile. |
| Cloud backend | Data breach, API exploitation, session hijacking | **Adequate.** Standard web application threats. |
| Sensor inputs | Adversarial neural signal injection | **Good.** Domain-specific attack surface unique to neurosecurity. |
| Protocol layer | State machine manipulation, protocol confusion | **Good.** Protocol-level attacks are well-covered. |

### 3.2 Kill Chain Documentation

The 7-stage kill chain documented in the threat models provides a structured progression from reconnaissance through exfiltration/persistence. This is **well-executed** and follows established frameworks ( Lockheed Martin Kill Chain / MITRE ATT&CK).

### 3.3 Undocumented Attack Surfaces

The following attack surfaces are present in the platform but absent from the threat models:

- **Web API attack surface:** The REST API and WebSocket endpoint accept external input with minimal validation. This surface is entirely undocumented in the threat models.
- **MCP server attack surface:** The MCP interface exposes clinician operations over a network socket with weak authentication. Not documented.
- **Build/CI pipeline attack surface:** The dependency management system (poisoned lockfile, unscanned Cargo dependencies) represents a supply chain attack surface. Not documented.
- **`cargo run` with user input:** The web server compiles and executes arbitrary Rust code. This is the single most dangerous attack surface in the platform and is absent from the threat models.
- **QEMU firmware execution:** User-provided firmware paths executed with full host privileges. Not documented.

---

## 4. STRIDE Analysis

**Rating: NEEDS IMPROVEMENT (C)**

### 4.1 STRIDE Framework Application

The threat models apply the STRIDE framework (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) to identified threats. This is a **good** structural choice for medical device threat modeling.

### 4.2 Stale Cross-Reference (CRITICAL DOCUMENTATION BUG)

`STRIDE.md` references `security.py` as the implementation module for STRIDE-related controls. However, the codebase has been refactored: `security.py` no longer exists. Its functionality has been split into:

- `detection.py` — security event detection and monitoring
- `clinical.py` — clinical safety controls and guardrails

This means that **any developer or auditor following STRIDE.md references will encounter broken links and incorrect module references**. This is a documentation integrity issue that undermines the entire STRIDE analysis:

- Threat mitigations listed in STRIDE.md cannot be traced to their implementation.
- Auditors cannot verify that STRIDE-identified threats have been adequately mitigated.
- New developers cannot understand the security architecture by following the documented references.

### 4.3 STRIDE Coverage Gaps

The STRIDE analysis focuses on device-level threats. The following STRIDE categories are underrepresented for platform-level threats:

- **Spoofing:** The single shared Bearer token (Phase 4 AUTHZ-001) makes spoofing trivial for any web API client — once the token is known, all clients are indistinguishable.
- **Tampering:** The poisoned lockfile (Phase 4 DEP-001) represents a tampering threat to the build process.
- **Elevation of Privilege:** The unsandboxed `cargo run` (Phase 4 PRIV-001) and QEMU execution (Phase 4 PRIV-002) represent privilege elevation from web API user to host process.

---

## 5. MITRE ATT&CK Mapping

**Rating: DEFICIENT (D)**

### 5.1 Current State

`MITRE.md` provides a thin mapping of identified threats to MITRE ATT&CK techniques. However:

- **Does not reference the YAML threat models:** The MITRE mapping appears to be a standalone document rather than an index into the detailed YAML models.
- **Incomplete coverage:** Not all threats identified in the YAML models are mapped to MITRE techniques.
- **No technique-level detail:** Where mappings exist, they lack the specificity needed for defensive planning (e.g., technique ID, sub-technique, data sources, mitigations).

### 5.2 Expected Integration

A robust MITRE mapping should:

1. Reference each threat in the YAML models by ID.
2. Map to specific ATT&CK technique and sub-technique IDs.
3. Include the applicable tactic (e.g., TA0001 - Initial Access).
4. Identify defensive mitigations from the ATT&CK mitigations matrix.
5. Suggest detection data sources for each technique.

The current MITRE.md does none of these systematically.

---

## 6. Threat Actor Coverage

**Rating: NEEDS IMPROVEMENT (C-)**

### 6.1 Documented Threat Actors

The capability levels (L0–L6) implicitly define threat actors by capability, which is a **good** approach. The threat models also describe specific actor archetypes appropriate to the medical device domain.

### 6.2 Missing Threat Actors

The following threat actors are **absent** from the threat models but are directly relevant to the platform:

#### 6.2.1 Insider Developer

A developer with commit access to the Vireon repository can:
- Introduce vulnerable dependencies via the poisoned lockfile.
- Disable security controls (e.g., set `SecurityConfig.enabled = False` as the default).
- Weaken cryptographic parameters (e.g., HKDF salt=None, AES-GCM AAD=None).
- Introduce backdoors in the NeuroDSL compiler or VM.
- Modify the plugin whitelist to include malicious plugins.

The threat models do not consider insider threats to the simulation platform itself, only to the simulated devices.

#### 6.2.2 CI/CD Pipeline Attacker

An attacker who compromises the CI/CD pipeline can:
- Inject malicious code during the build process.
- Replace verified dependencies with compromised versions (supply chain attack).
- Tamper with build artifacts before deployment.
- Modify Docker images during the build process.

Given the poisoned lockfile finding, this threat actor is not merely theoretical — there is evidence that the pipeline's integrity is already compromised.

#### 6.2.3 Dependency Supply Chain Attacker

An attacker who compromises an upstream dependency can:
- Inject malicious code via a compromised Python package (dependency confusion, typosquatting).
- Target the Cargo ecosystem (no Dependabot coverage for Rust dependencies — Phase 4 finding DEP-002).
- Exploit the websockets version conflict (Phase 4 finding DEP-003) to force installation of a vulnerable version.

#### 6.2.4 Platform User / Researcher

A legitimate user of the Vireon platform (e.g., a neurosecurity researcher) may:
- Exploit the unsandboxed `cargo run` to execute arbitrary code on the host.
- Use the platform's capabilities to develop and test attacks against real neural interfaces.
- Extract sensitive patient simulation data from the platform.

### 6.3 Threat Actor Motivation Gap

The threat models focus on attackers motivated by patient harm or data theft. The simulation platform introduces a new motivation: **using the platform as a weapon development tool**. An attacker could use Vireon to develop, test, and refine attacks against real neural interfaces before deploying them against actual patients. This meta-threat is not addressed.

---

## 7. Missing Attack Classes

**Rating: DEFICIENT (D+)**

### 7.1 Denial of Service Against the Simulation Platform

The threat models cover DoS against simulated devices but not against the Vireon platform itself:

- **Resource exhaustion via NeuroDSL:** A malicious NeuroDSL program could create infinite loops, exhaust memory, or consume excessive CPU in the unsandboxed VM.
- **WebSocket connection flooding:** The WebSocket endpoint has no rate limiting. An attacker could open thousands of connections.
- **`cargo run` resource exhaustion:** Compiling Rust code is CPU- and memory-intensive. An attacker could submit pathological source code that exhausts build resources.
- **QEMU instance flooding:** Multiple simultaneous QEMU instances with large firmware images could exhaust host memory.

### 7.2 Dependency Confusion and Typosquatting

The platform uses both Python (pip) and Rust (Cargo) dependencies. Neither ecosystem is protected against:

- **Dependency confusion:** An attacker publishes a package with the same name as an internal dependency on a public registry, causing the build system to install the malicious public version.
- **Typosquatting:** An attacker publishes packages with names similar to legitimate dependencies (e.g., `websockets` → `websocketz`).

The poisoned lockfile (Phase 4 DEP-001) suggests the dependency supply chain is already compromised, making these attack classes highly relevant.

### 7.3 Simulation Fidelity Attacks

An attacker could manipulate the simulation to produce false security assessments:

- **Trust score manipulation:** If ZTA trust scores can be influenced, an attacker could make an insecure configuration appear secure.
- **Guardrail bypass:** The G7 guardrail's trivial bypass (Phase 4 INVAL-002) means the simulation can be made to accept attack payloads it should reject.
- **Firmware signature weakness:** The hash-based "signature" (Phase 4 FW-001) means the simulation models a defense that would fail against a real adversary, producing false confidence.

---

## 8. Post-Compromise Assumptions

**Rating: DEFICIENT (D)**

### 8.1 Current State

The threat models do not document post-compromise assumptions. Specifically:

- **What happens after an attacker gains access to the web API?** The single shared Bearer token means full platform compromise is the default outcome, but this is not modeled.
- **What happens after firmware is compromised?** The anti-rollback mechanism prevents downgrade, but there is no documented recovery path.
- **What happens after the MCP server is compromised?** There is no credential rotation, no revocation mechanism.
- **What happens after a dependency is compromised?** There is no documented incident response for supply chain attacks.

### 8.2 Expected Post-Compromise Documentation

For a medical device security platform, post-compromise assumptions should include:

1. **Detection capability:** How quickly can a compromise be detected? What are the indicators of compromise (IoCs)?
2. **Containment:** What mechanisms exist to limit the blast radius of a compromise?
3. **Recovery:** What is the recovery procedure? How are credentials rotated? How is firmware integrity restored?
4. **Attribution:** What forensic data is available post-compromise?

The current threat models provide none of this.

---

## 9. Recovery Assumptions

**Rating: DEFICIENT (D-)**

### 9.1 Current State

Recovery assumptions are **minimal** in the threat model documentation:

- No documented backup/restore procedures for simulation state.
- No credential rotation procedures (tokens and keys persist until process restart).
- No firmware recovery mechanisms beyond anti-rollback prevention.
- No incident response plan.

### 9.2 Impact

The absence of recovery assumptions is particularly concerning for a neurosecurity simulation platform because:

- **Session state loss:** If the platform is compromised during an active simulation session, therapy state may be lost or corrupted.
- **Trust state corruption:** If ZTA trust scores are manipulated, there is no documented mechanism to reset trust state.
- **Database integrity:** If patient simulation data is tampered with, there is no documented integrity verification or restoration procedure.

---

## 10. Undocumented Assumptions

### 10.1 Python Runtime Is Trusted

The threat models implicitly assume the Python runtime is a trusted compute base. However:

- CPython has a history of memory safety vulnerabilities.
- The platform does not pin to a specific CPython version (no `.python-version` or equivalent).
- If the Python runtime is compromised, all security controls implemented in Python are bypassed.

### 10.2 OS Cryptographic Libraries Are Correct

The platform relies on Python's `hashlib`, `hmac`, and `secrets` modules, which delegate to OpenSSL. The threat models assume these libraries correctly implement their specified algorithms. While this is generally reasonable, it should be documented as an explicit assumption, particularly given the history of OpenSSL vulnerabilities (Heartbleed, etc.).

### 10.3 Single-Threaded Attack Execution

Several security controls appear to assume single-threaded execution:

- The BiometricGate failure counter is not documented as thread-safe.
- ZTA trust score updates are not documented as atomic.
- The NeuroDSL VM state is not documented as thread-safe.

However, the web server handles multiple concurrent connections, and thread-safety bugs have been identified in the codebase. This assumption is **contradicted by the actual execution model** and should be documented and addressed.

### 10.4 Attacker Cannot Modify Simulation Code

The threat models focus on external attackers interacting with the simulation. They do not consider an attacker who can modify the simulation code itself (e.g., via a supply chain attack, insider threat, or code injection through the unsandboxed `cargo run`). This is a critical blind spot given the multiple code execution vectors identified in Phase 4.

### 10.5 Network Layer Is Trustworthy

The threat models document application-layer threats but assume the network layer (TCP/IP, TLS) is correctly implemented and uncompromised. This is a standard assumption but should be explicit, particularly for the BLE link where TLS is not used (BLE uses its own security mechanisms).

### 10.6 Simulation Fidelity Reflects Reality

The entire value proposition of Vireon rests on the assumption that its security simulations accurately reflect real-world neurodevice security. However:

- The firmware "signature" is a hash, not a real cryptographic signature (Phase 4 FW-001).
- The NeuroDSL VM is unsandboxed, unlike real embedded environments (Phase 4 PRIV-003).
- The AES-GCM implementation omits AAD, unlike properly secured medical devices (Phase 4 SEC-001).

These implementation weaknesses mean the simulation may produce **false negative results** — suggesting a defense is effective when it would fail against a real adversary.

---

## 11. Structural Assessment of YAML Threat Models

### 11.1 Strengths

- **Epistemic bounding:** The threat models explicitly avoid speculative threats (e.g., "mind reading" via neural interfaces). This disciplined approach is commendable and rare in security documentation.
- **In-scope/out-of-scope lists:** Clear delineation of what the models cover and what they do not. This manages reviewer expectations and identifies gaps intentionally.
- **STRIDE and MITRE mappings:** The intent to map to established frameworks is correct, even if the execution is incomplete.
- **Per-device specialization:** Separate models for DBS, VNS, Cochlear, and BCI demonstrate understanding that different neural interfaces have different threat profiles.
- **Kill chain structure:** The 7-stage kill chain provides a systematic attack progression model.

### 11.2 Weaknesses

- **No severity/risk scoring:** Threats are identified but not prioritized. Without severity ratings, it is impossible to triage mitigation efforts.
- **No likelihood estimation:** Even qualitative likelihood (High/Medium/Low) would improve the models' utility for resource allocation.
- **No mitigation tracking:** Threats are identified but there is no tracking of which mitigations are implemented, planned, or deferred.
- **Stale references:** STRIDE.md references `security.py` which has been refactored to `detection.py` and `clinical.py`.
- **No versioning:** The threat model documents do not include version numbers, making it impossible to track which version of the threat model corresponds to which version of the platform.

---

## 12. Recommendations

### 12.1 Immediate (P0)

1. **Fix STRIDE.md references:** Update all references from `security.py` to `detection.py` and `clinical.py`. This is a documentation integrity fix that unblocks all downstream audit work.
2. **Add platform-level threats to YAML models:** The threat models must cover threats to the Vireon platform itself, not just the simulated devices. At minimum, add threat entries for: web API compromise, `cargo run` code execution, QEMU firmware execution, and dependency supply chain attacks.
3. **Add missing threat actors:** Include insider developer, CI/CD pipeline attacker, and dependency supply chain attacker in the threat actor catalog.

### 12.2 Short-Term (P1)

4. **Add severity/risk scoring to all YAML threat models:** Implement a qualitative or semi-quantitative risk scoring system (e.g., DREAD, CVSS-based, or custom) for each identified threat.
5. **Rewrite MITRE.md as a cross-reference index:** Map each YAML threat model entry to specific ATT&CK technique IDs and sub-techniques. Include tactic, data sources, and mitigations.
6. **Document post-compromise assumptions:** For each critical asset, document the expected detection time, containment mechanisms, and recovery procedures.
7. **Document implicit assumptions:** Add a dedicated "Assumptions" section to the threat model documentation covering: trusted Python runtime, trusted OS crypto libraries, single-threaded execution limits, and simulation fidelity boundaries.

### 12.3 Medium-Term (P2)

8. **Add missing assets:** Document MCP secret key, WebSocket Bearer token, NeuroDSL program source, plugin registry state, and ZTA trust scores as named assets with sensitivity classifications.
9. **Add attack classes:** Document DoS against the platform, dependency confusion, typosquatting, and simulation fidelity attacks.
10. **Implement threat model versioning:** Add version numbers to all threat model documents and establish a review/update cadence tied to platform releases.
11. **Add mitigation tracking:** For each identified threat, track mitigation status (Implemented / Planned / Accepted Risk / Deferred) and link to specific code artifacts (file, function, line number).

### 12.4 Long-Term (P3)

12. **Automated threat model validation:** Develop tooling to automatically verify that threat model references point to existing code, that identified mitigations are still present, and that new code paths are covered by existing threat entries.
13. **Simulation fidelity audit:** Conduct a systematic comparison between Vireon's security implementations and real-world neurodevice security mechanisms to document and quantify fidelity gaps.

---

## Summary Matrix

| # | Category | Rating | Key Finding |
|---|---|---|---|
| 1 | Asset Identification | B | Good domain assets; missing platform assets |
| 2 | Trust Boundaries | B+ | Well-structured; missing platform boundaries |
| 3 | Attack Surface | B | Comprehensive for devices; missing platform surfaces |
| 4 | STRIDE Analysis | C | Good framework; stale references to refactored code |
| 5 | MITRE Mapping | D | Thin; doesn't reference YAML models |
| 6 | Threat Actors | C- | Good capability levels; missing supply chain/insider |
| 7 | Attack Classes | D+ | Missing DoS, dependency confusion, fidelity attacks |
| 8 | Post-Compromise | D | Not documented |
| 9 | Recovery | D- | Minimal |
| 10 | Assumptions | D | Multiple undocumented implicit assumptions |

---

## Conclusion

The Vireon threat model documentation demonstrates genuine expertise in neurodevice security and a disciplined approach to epistemic bounding. The YAML threat models are well-structured and the capability-level framework is a notable strength. However, the documentation has a critical blind spot: it models threats to *simulated devices* while largely ignoring threats to the *simulation platform itself*. Given that the platform contains multiple unrestricted code execution vectors (unsandboxed `cargo run`, unsandboxed QEMU), a poisoned dependency lockfile, and a single shared authentication token, the platform-level threat surface is arguably more severe than the device-level threats being modeled.

The stale STRIDE.md references and thin MITRE mapping suggest the threat models have not been maintained in sync with codebase evolution. The absence of severity scoring, post-compromise assumptions, and recovery procedures means the threat models cannot effectively drive security investment decisions.

Most importantly, the undocumented assumption that simulation fidelity reflects reality is challenged by multiple Phase 4 findings: the firmware "signature" is not a real signature, the AES-GCM implementation omits AAD, and the VM is unsandboxed. If the simulation's security controls do not accurately model real-world defenses, the threat models built on top of those simulations may produce misleading security assessments. This meta-issue — the reliability of the simulation as a security analysis tool — should be the primary concern of subsequent audit phases.

## 13. Implementation Evaluation Status

**Date:** 2026-07-16
**Evaluator:** Agent

### Addressed Findings
- **None**. The repository remediation phases have not yet targeted the threat model artifacts (`threat_models/*.yaml`, `STRIDE.md`, `MITRE.md`).

### Persisting / Unaddressed Findings
- **4.2 Stale Cross-Reference**: STILL PRESENT. `STRIDE.md` still refers to the non-existent `security.py` module.
- **11.2 Weaknesses (No severity/risk scoring)**: STILL PRESENT. Threat models remain qualitative without DREAD or CVSS scoring.
- **5.1 MITRE ATT&CK Mapping**: STILL PRESENT. `MITRE.md` mapping remains thin and detached from the core YAML models.
- **2.3 Undocumented Trust Boundaries**: STILL PRESENT. Platform-level vulnerabilities (e.g. `cargo run`, web API) are absent from the simulation-centric threat models.

**Conclusion:** The threat models require a significant overhaul to accurately reflect the platform's current architecture (fixing `STRIDE.md` references) and to incorporate threats targeting the simulation platform itself, rather than exclusively focusing on the modeled neurodevices.