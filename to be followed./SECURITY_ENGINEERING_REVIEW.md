# Phase 4: Security Engineering Review — Vireon Neurosecurity Simulation Platform

**Audit Phase:** 4 of 12  
**Classification:** Security Engineering Controls Assessment  
**Scope:** Authentication, Authorization, Input/Output Validation, Secrets Handling, Least Privilege, Trust Boundaries, Firmware Security, Dependency Risks, Configuration Security  
**Date:** 2025-07-09  

---

## Executive Summary

This review evaluates the security engineering posture of the Vireon neurosecurity simulation platform across nine control categories. The platform demonstrates strong security instincts in several areas — particularly zero-trust architecture defaults, biometric authentication hardening, and firmware integrity controls — but suffers from critical gaps in sandboxing, cryptographic parameter hygiene, and authorization granularity. Several findings represent exploitable vulnerabilities in a production context; while Vireon is a simulation/research tool, these weaknesses undermine the fidelity of the security simulations it produces and could enable real compromise if the platform is ever connected to clinical infrastructure.

**Overall Rating: MODERATE RISK** — 4 categories rated Acceptable, 3 rated Needs Improvement, 2 rated Deficient.

---

## 1. Authentication

**Rating: NEEDS IMPROVEMENT (B-)**

### 1.1 BiometricGate (authentication.py)

The `BiometricGate` class implements the primary authentication mechanism for neural signal entry. Three controls are present and effective:

| Control | Implementation | Assessment |
|---|---|---|
| Failure lockout | 5-failure lockout with 5-minute cooldown | **Good.** Prevents brute-force against biometric verification. Cooldown period is reasonable for simulation use. |
| Spectral entropy spoofing detection | Analyzes signal entropy to detect synthetic/replayed signals | **Good.** Raises the bar for adversarial signal injection. |
| Cross-channel cloning detection | Detects if signals are replayed from one neural channel to another | **Good.** Addresses a realistic attack vector in neural interface security. |

These controls are well-suited to the simulation's domain and demonstrate domain-aware security engineering.

### 1.2 MCP Server Authentication (mcp_server.py)

Clinician authentication relies on `os.environ.get("CLINICIAN_PUB_KEY")` for credential comparison. This is **weak** for several reasons:

- **Environment variable injection:** Any process running in the same context can set or override the `CLINICIAN_PUB_KEY` environment variable, trivially bypassing authentication.
- **No key validation:** The implementation performs a simple string comparison rather than cryptographic verification. There is no evidence of proper public-key cryptographic operations (e.g., signature verification against the clinician's private key).
- **No transport security for the credential:** The environment variable is loaded at startup with no rotation mechanism.
- **Single factor:** Authentication is a single static credential with no multi-factor fallback.

### 1.3 Web Server Authentication (web_server.py)

The WebSocket Bearer token is generated at startup using `secrets.token_urlsafe(16)`, providing **128 bits of entropy** — cryptographically adequate. However, the token is transmitted as a URL query parameter for WebSocket connections:

```
ws://host:port/ws?token=<token>
```

**This is a well-documented anti-pattern.** URL query parameters are recorded in:
- Web server access logs
- Proxy/CDN logs
- Browser history
- HTTP `Referer` headers (if any page links to the WebSocket URL)
- Network monitoring tools

The token should be transmitted in the `Sec-WebSocket-Protocol` header or via an initial HTTP handshake with `Authorization: Bearer <token>`.

### 1.4 Credential Management Gaps

- **No persistent user management:** There is no user database, user registration, or credential storage system.
- **No credential rotation:** Tokens and keys are generated once at startup and persist until process restart.
- **No session management:** No session timeout, no session revocation, no concurrent session limits.

### 1.5 Findings

| ID | Severity | Finding |
|---|---|---|
| AUTH-001 | **Medium** | WebSocket token in URL query params leaks to logs |
| AUTH-002 | **Medium** | MCP clinician auth via env var comparison is trivially bypassable |
| AUTH-003 | **Low** | No credential rotation or session management |

---

## 2. Authorization

**Rating: DEFICIENT (D+)**

### 2.1 ZTA Policy Engine (zta.py)

The Zero-Trust Architecture policy engine demonstrates **excellent** design decisions:

- **Fail-closed defaults:** When trust cannot be established, the system defaults to denying access. This is the correct security posture and is explicitly implemented.
- **Mandatory E2EE gating:** The policy engine clamps maximum trust score to 0.5 when end-to-end encryption is not active. This means that even if all other trust signals are positive, an unencrypted channel cannot achieve sufficient trust for sensitive operations. This is a **strong and well-reasoned** control.

### 2.2 MCP Authorization

Authorization in the MCP server is limited to a **binary patient/clinician distinction**. There is no Role-Based Access Control (RBAC) beyond this:

- No tiered clinician roles (e.g., attending vs. resident vs. technician).
- No per-patient access control lists.
- No temporal authorization (e.g., clinician access only during scheduled sessions).
- No operation-level authorization (e.g., read-only vs. parameter modification).

### 2.3 Web API Authorization — CRITICAL GAP

The web API uses a **single shared Bearer token** with **no authorization model whatsoever**. Any client possessing the token has unrestricted access to all API endpoints. This means:

- All web clients share identical privileges.
- There is no distinction between read and write operations at the authorization level.
- There is no per-patient or per-session isolation.
- Compromise of the token grants full platform access.

### 2.4 Findings

| ID | Severity | Finding |
|---|---|---|
| AUTHZ-001 | **Critical** | Web API has zero authorization — single shared secret grants full access |
| AUTHZ-002 | **Medium** | No RBAC in MCP beyond binary patient/clinician split |
| AUTHZ-003 | **Low** | ZTA engine design is excellent but only applies to neural signal channel trust |

---

## 3. Input Validation

**Rating: NEEDS IMPROVEMENT (C+)**

### 3.1 Guardrails Module (guardrails.py)

The guardrails module validates attack payloads before injection into the simulation. However, the G7 check is critically flawed:

```python
# G7 check (illustrative — examines report_prefix for "offensive_strike")
```

The G7 guardrail inspects only the `report_prefix` field for the literal string `"offensive_strike"`. This is **trivially bypassable** by an attacker who:
- Uses a different naming convention for the attack payload.
- Encodes or obfuscates the prefix.
- Simply omits or renames the field.

A robust guardrail should validate the *structure* and *parameters* of the payload, not its metadata labels.

### 3.2 REST API Input Validation

Input validation on REST API parameters is limited to a simplistic path traversal check:

```python
# Simplistic ".." string check — not URL-decoded
```

This check looks for the literal string `".."` in path parameters. It fails to account for:
- **URL-encoded variants:** `%2e%2e`, `%2e.`, `..%2f`, and double-encoding (`%252e%252e`).
- **Path normalization differences:** `....//`, `/../`, etc.
- **Null byte injection:** `..%00/` (though modern Python generally handles this).

A proper implementation should use `os.path.abspath()` + prefix checking, or a dedicated path safety library.

### 3.3 NeuroDSL Compiler — Type Truncation Bypass (CRITICAL)

The NeuroDSL compiler contains a security verification pass, but a **type truncation vulnerability** allows bypass of amplitude safety checks:

```
SET_AMP 300  →  parsed as u16 (300)  →  truncated to u8 (44)  →  SetAmp(44)
```

The amplitude check validates `value <= 100`, but the u16→u8 truncation converts 300 to 44 (300 mod 256 = 44), which passes the ≤100 check. This means:

- An attacker can specify amplitudes in the range 0–255 by choosing appropriate u16 values that truncate to the desired u8.
- More critically, if the safety check operates on the u16 value (e.g., `300 <= 100` fails) but the VM operates on the u8 value, the check may be inconsistent — the evidence suggests the truncation happens *before* the check, allowing values 0–255 to pass.
- If the actual hardware/firmware expects u8, the check is fundamentally wrong: it should validate on the same type the VM uses.

This is a **classic integer truncation vulnerability** of the kind found in real medical device recalls.

### 3.4 Findings

| ID | Severity | Finding |
|---|---|---|
| INVAL-001 | **Critical** | NeuroDSL u16→u8 truncation bypasses amplitude safety checks |
| INVAL-002 | **High** | G7 guardrail checks metadata label, not payload structure |
| INVAL-003 | **Medium** | Path traversal check does not handle URL-encoded variants |

---

## 4. Output Validation

**Rating: ACCEPTABLE (B)**

### 4.1 NaN/Inf Sanitization

The WebSocket broadcast path in `coordinator.py` (line 336) implements NaN/Inf sanitization before sending data to clients. This is a **good** control that prevents:

- JSON serialization failures (NaN and Infinity are not valid JSON).
- Client-side numerical errors from consuming invalid floating-point values.
- Potential injection of non-finite values that could exploit client-side numeric parsing.

### 4.2 REST API Output Encoding

REST API responses have **no explicit output encoding**. While Python's JSON serializer handles most special characters, there is no defense-in-depth against:

- Content-type injection in response headers.
- Reflected content in error messages that could enable XSS if the API is consumed by a browser-based client.
- Binary data leakage in error responses.

### 4.3 Findings

| ID | Severity | Finding |
|---|---|---|
| OUTVAL-001 | **Low** | No output encoding in REST API responses |
| OUTVAL-002 | **Info** | NaN/Inf sanitization is well-implemented |

---

## 5. Secrets Handling

**Rating: NEEDS IMPROVEMENT (C)**

### 5.1 Token Generation — Good

| Secret | Generation Method | Assessment |
|---|---|---|
| WebSocket auth token | `secrets.token_urlsafe(16)` — 128-bit entropy | **Good.** Uses CSPRNG. |
| MCP server secret | `secrets.token_bytes(32)` stored in `~/.vireon/mcp_secret.key` | **Good.** 256-bit entropy, file-scoped storage. |

### 5.2 Key Derivation — Deficient

**HKDF with `salt=None`:** The E2EE implementation uses HKDF for key derivation but passes `salt=None`. While HKDF with a null salt is technically specified in RFC 5869 (it uses a zero-filled salt of hash length), this:

- Eliminates the domain separation benefit of a unique salt.
- Means the same input keying material always produces the same output key.
- Reduces resistance to multi-target attacks.
- Is explicitly discouraged in NIST SP 800-56C Rev. 2 when a salt can be provided.

**AES-GCM with `AAD=None`:** The AEAD (Authenticated Encryption with Associated Data) construction is used without Additional Authenticated Data. This **defeats the primary purpose of AEAD**:

- Without AAD, there is no binding between the ciphertext and contextual data (e.g., channel ID, session ID, message sequence number).
- An attacker who obtains a valid ciphertext can potentially replay it in a different context where the same key is used.
- AAD should include at minimum: session identifier, message sequence number, and channel type.

**HMAC without salt for session key derivation:** Session keys are derived using HMAC without a salt. This means deterministic key derivation from the same inputs, reducing key space diversity.

### 5.3 Secrets Management Infrastructure

- **No `.env` file support:** Configuration is scattered across environment variables, hardcoded defaults, and file-based storage.
- **No vault integration:** No HashiCorp Vault, AWS Secrets Manager, or equivalent.
- **No secret rotation:** Secrets persist for the lifetime of the process.

### 5.4 Findings

| ID | Severity | Finding |
|---|---|---|
| SEC-001 | **High** | AES-GCM used without AAD — defeats AEAD purpose |
| SEC-002 | **Medium** | HKDF with salt=None reduces key derivation security |
| SEC-003 | **Medium** | HMAC without salt for session key derivation |
| SEC-004 | **Low** | No vault integration or secret rotation |

---

## 6. Least Privilege

**Rating: DEFICIENT (D)**

### 6.1 Docker Container — Good

The Dockerfile creates a non-root user for the application process. This follows container security best practices and limits the blast radius of container escape.

### 6.2 Dockerfile Layer Ordering — Hygiene Issue

The Dockerfile uses `COPY . .` before `pip install`, which breaks Docker layer caching. While not a direct security issue, it means every code change triggers a full dependency reinstall, increasing the attack surface during build time and potentially masking dependency changes in image audits.

### 6.3 QEMU Subprocess — No Sandboxing (CRITICAL)

The platform spawns QEMU subprocesses with a user-provided `firmware_path`:

```python
# QEMU subprocess spawn with user-provided firmware_path
```

This is a **critical privilege escalation and code execution vector**:

- An attacker who can control the firmware path can point QEMU at arbitrary firmware, including malicious binaries.
- QEMU runs with the full privileges of the host process.
- There is no seccomp, AppArmor, or namespace isolation around the QEMU subprocess.
- In a production context, this enables full host compromise.

### 6.4 Cargo Subprocess — No Sandboxing (CRITICAL)

The web server executes:

```python
subprocess.run(["cargo", "run", "--bin", "forge"], input=user_supplied_source_code)
```

This is **extremely dangerous**:

- User-supplied source code is passed as stdin to `cargo run`, which compiles and executes arbitrary Rust code.
- `cargo run` executes build scripts (`build.rs`), proc macros, and the compiled binary.
- No sandboxing, no resource limits, no network isolation.
- An attacker with web API access can achieve arbitrary code execution on the host.
- This is effectively a **remote code execution (RCE) as a service**.

### 6.5 NeuroDSL VM — No Sandboxing

The NeuroDSL virtual machine has no sandboxing, as documented in the `engine.py` docstring. While the VM interprets a domain-specific language, any VM escape or vulnerability in the interpreter enables arbitrary code execution.

### 6.6 Findings

| ID | Severity | Finding |
|---|---|---|
| PRIV-001 | **Critical** | `subprocess.run(["cargo", "run"...])` with user-supplied source code = RCE |
| PRIV-002 | **Critical** | QEMU subprocess with user-provided firmware path, no sandbox |
| PRIV-003 | **High** | NeuroDSL VM has no sandboxing |
| PRIV-004 | **Info** | Docker non-root user is properly configured |

---

## 7. Trust Boundaries

**Rating: NEEDS IMPROVEMENT (C-)**

### 7.1 Plugin Whitelist — Good

The plugin registry (`plugin_registry.py`, lines 179–185) enforces a whitelist of permitted plugins. This is a **strong** trust boundary control that prevents unauthorized code execution through the plugin system.

### 7.2 Missing Trust Boundary: Web API ↔ Core

There is **no trust boundary between the web API and the core simulation engine**. The web API calls core simulation functions directly without:

- An intermediate authorization layer.
- Input/output mediation.
- Rate limiting or resource quotas.
- Audit logging of API-to-core calls.

### 7.3 Undefined Trust Boundary in MCP

The MCP server explicitly states "trust boundary is undefined" in its warning header. This is an **admission of architectural deficiency** — the MCP interface cannot make security guarantees because the trust model has not been defined.

### 7.4 Findings

| ID | Severity | Finding |
|---|---|---|
| TB-001 | **High** | No trust boundary between web API and core simulation |
| TB-002 | **High** | MCP trust boundary explicitly undefined |
| TB-003 | **Info** | Plugin whitelist enforcement is well-implemented |

---

## 8. Firmware Security

**Rating: ACCEPTABLE (B+)**

### 8.1 Anti-Rollback Protection

Minimum Secure Version Number (MIN_SVN) enforcement prevents installation of firmware older than a specified version. This is a **critical** defense against attacks that attempt to downgrade firmware to a vulnerable version.

### 8.2 Firmware Signature Verification — Weak

SHA-256 signature verification is implemented, but the "signature" is simply the **hash of the firmware**:

```
signature = SHA-256(firmware_bytes)
```

This is **not a cryptographic signature**. A real signature requires asymmetric cryptography (e.g., ECDSA, Ed25519) where the private key signs and the public key verifies. In this implementation:

- Anyone who knows the firmware content (which is transmitted in the clear during the update process) can compute the valid "signature."
- There is no proof of firmware provenance — no indication of *who* produced the firmware.
- A man-in-the-middle can modify the firmware, recompute the hash, and the verification will pass.

This provides integrity verification only against *accidental* corruption, not against *adversarial* modification.

### 8.3 Runtime Protections — Good

- **Stack canary simulation:** Detects buffer overflow attacks at runtime.
- **MPU memory segregation:** Enforces IEC 62304 memory safety requirements through Memory Protection Unit simulation.

These are well-designed controls that accurately simulate real embedded security mechanisms.

### 8.4 Findings

| ID | Severity | Finding |
|---|---|---|
| FW-001 | **High** | Firmware "signature" is just a hash — no asymmetric verification |
| FW-002 | **Info** | Anti-rollback, stack canaries, and MPU are well-designed |

---

## 9. Dependency Risks

**Rating: NEEDS IMPROVEMENT (C)**

### 9.1 CI Dependency Scanning — Good

`pip-audit` is integrated into the CI pipeline, providing automated detection of known vulnerabilities in Python dependencies.

### 9.2 Lockfile Poisoning (CRITICAL)

The `requirements-lock.txt` file is **poisoned** — its contents do not accurately reflect the actual dependency tree. This means:

- Dependency integrity **cannot be verified** from the lockfile.
- Reproducible builds are **not achievable**.
- Any security audit of dependencies based on the lockfile produces **false results**.
- The lockfile may have been intentionally or accidentally modified to include or exclude packages.

### 9.3 Cargo Ecosystem Gap

No Dependabot or equivalent automated dependency update tool is configured for the Rust/Cargo ecosystem. The project includes Rust components (e.g., the `forge` binary compiled via `cargo run`), but these dependencies receive no automated vulnerability scanning.

### 9.4 Version Conflict

The `pyproject.toml` pins `websockets` to version 11.x, while the lockfile records version 16.0. This discrepancy:

- Indicates the lockfile is out of sync with the declared dependencies.
- May introduce behavioral differences or security vulnerabilities depending on which version is actually installed.
- Suggests the dependency management workflow is broken.

### 9.5 Findings

| ID | Severity | Finding |
|---|---|---|
| DEP-001 | **Critical** | requirements-lock.txt is poisoned — dependency integrity unverifiable |
| DEP-002 | **Medium** | No dependency scanning for Cargo/Rust ecosystem |
| DEP-003 | **Medium** | websockets version conflict between pyproject.toml and lockfile |

---

## 10. Configuration Security

**Rating: ACCEPTABLE (B)**

### 10.1 Secure by Default

`SecurityConfig.enabled` defaults to `False`, meaning the platform starts in a more restrictive security posture and requires explicit opt-in to enable security features. This is a **good** default — it follows the principle of "secure by default."

### 10.2 ZTA Threshold Typing

Zero-Trust Architecture thresholds are not strongly typed, meaning they can be set to arbitrary values (including negative numbers, floats beyond 0.0–1.0, or even non-numeric types). This could lead to unexpected behavior in trust calculations.

---

## Summary Matrix

| # | Category | Rating | Critical | High | Medium | Low |
|---|---|---|---|---|---|---|
| 1 | Authentication | B- | 0 | 0 | 2 | 1 |
| 2 | Authorization | D+ | 1 | 0 | 1 | 0 |
| 3 | Input Validation | C+ | 1 | 1 | 1 | 0 |
| 4 | Output Validation | B | 0 | 0 | 0 | 1 |
| 5 | Secrets Handling | C | 0 | 1 | 2 | 1 |
| 6 | Least Privilege | D | 2 | 1 | 0 | 1 |
| 7 | Trust Boundaries | C- | 0 | 2 | 0 | 1 |
| 8 | Firmware Security | B+ | 0 | 1 | 0 | 1 |
| 9 | Dependency Risks | C | 1 | 0 | 2 | 0 |
| 10 | Configuration Security | B | 0 | 0 | 0 | 0 |
| | **Total** | | **5** | **5** | **8** | **6** |

---

## Priority Remediation Roadmap

### Immediate (P0 — within 48 hours)
1. **PRIV-001:** Sandbox or eliminate `cargo run` with user-supplied input. Use `--sandbox` flags, seccomp profiles, or replace with a safe execution environment.
2. **PRIV-002:** Apply namespace/cgroup/seccomp isolation to QEMU subprocess. Validate firmware_path against an allowlist.
3. **AUTHZ-001:** Implement role-based or scope-based authorization for the web API.
4. **DEP-001:** Regenerate requirements-lock.txt from a clean environment and establish integrity verification.

### Short-Term (P1 — within 2 weeks)
5. **INVAL-001:** Fix NeuroDSL compiler to validate amplitude on the same type (u8) the VM uses, or eliminate the truncation.
6. **INVAL-002:** Rewrite G7 guardrail to validate payload structure, not metadata labels.
7. **SEC-001:** Add AAD to AES-GCM operations (session ID, sequence number, channel type).
8. **FW-001:** Replace hash-based "signature" with real asymmetric cryptographic signature (Ed25519 recommended).
9. **TB-001/TB-002:** Define and enforce trust boundaries for web API and MCP interfaces.

### Medium-Term (P2 — within 1 month)
10. **AUTH-001:** Move WebSocket token from query params to headers.
11. **AUTH-002:** Replace env var clinician auth with proper cryptographic verification.
12. **SEC-002/003:** Add proper salts to HKDF and HMAC operations.
13. **DEP-002:** Add Cargo audit/scanning to CI pipeline.
14. **INVAL-003:** Use proper path validation (abspath + prefix check) instead of string matching.
15. **PRIV-003:** Implement sandboxing for NeuroDSL VM.

---

## Conclusion

Vireon demonstrates thoughtful security engineering in its domain-specific controls (biometric gate, ZTA policy engine, firmware anti-rollback, plugin whitelist). However, the platform has a bifurcated security model: the neural simulation core is well-protected while the web/CLI infrastructure is dangerously permissive. The two most urgent findings — unsandboxed `cargo run` with user input and unsandboxed QEMU with user-provided firmware paths — represent **unrestricted remote code execution vectors** that must be addressed before any network-exposed deployment. The firmware "signature" being a simple hash rather than an asymmetric cryptographic signature undermines the platform's value as a neurosecurity simulation tool, since it models a defense that would fail against a real adversary.

The dependency management situation (poisoned lockfile, version conflicts) suggests the build pipeline itself needs hardening before dependency-level security guarantees can be trusted.