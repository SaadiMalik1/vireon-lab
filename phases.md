You are NOT acting as a software engineer.

You are acting as a Principal Systems Architect, Distinguished Research Engineer, and Neurotechnology Security Advisor.

Your task is NOT to write code.

Your task is to define the architectural constitution that every future design decision must obey.

This document is the single source of truth for the project.

Every future feature, module, plugin, interface, or subsystem must be justified against this document.

If something conflicts with this constitution, recommend removing it regardless of implementation effort.

Treat this as the equivalent of an RFC or architecture manifesto.

----------------------------------------------------

CONTEXT
----------------------------------------------------

The current repository evolved from an educational neurotechnology security simulator.

During development it accumulated:

• attack simulation
• digital twins
• IDS
• firmware abstraction
• protocol simulation
• threat modelling
• benchmarking
• compliance tooling
• hardware abstraction
• plugins

The project is beginning to transition into something much larger.

The long-term vision is NOT to simulate proprietary devices such as Neuralink or Synchron.

Instead, the vision is to become a vendor-neutral validation framework that allows organizations to integrate their own proprietary firmware, protocols, decoders, threat models, digital twins, and validation plugins without exposing intellectual property.

Think of VIREON as analogous to:

• ROS for robotics
• Gazebo for robot simulation
• CARLA for autonomous driving
• LLVM for compiler infrastructure
• QEMU for hardware virtualization

The framework provides the runtime, orchestration, validation, benchmarking, reporting, and plugin ecosystem.

Vendors provide proprietary implementations.

The educational simulator will eventually become a separate project built on top of the framework.

----------------------------------------------------

OBJECTIVES
----------------------------------------------------

Produce a comprehensive architectural constitution.

Do NOT discuss implementation.

Reason only from systems architecture, software engineering, and long-term maintainability.

----------------------------------------------------

DELIVERABLES
----------------------------------------------------

1. Mission

Define the fundamental mission of VIREON.

This must fit into one sentence.

1. Vision

Describe what VIREON should become over the next 5–10 years.

1. Problem Statement

Identify the real problem VIREON exists to solve.

Challenge assumptions.

Avoid marketing language.

1. Why Existing Tools Are Insufficient

Compare conceptually against:

• BrainFlow
• MNE
• OpenBCI
• ROS
• Gazebo
• CARLA
• Simulink
• ns-3
• QEMU

Identify the architectural gap VIREON fills.

1. Core Principles

Define immutable principles.

Examples:

• Vendor neutrality
• Plugin-first architecture
• Language independence
• Explicit assumptions
• Scientific reproducibility
• Security by design
• Composability
• Extensibility
• Evidence before claims
• Open interfaces, proprietary implementations

Every future decision must align with these principles.

1. Scope

Clearly define:

What VIREON IS.

What VIREON IS NOT.

Be explicit.

Examples:

VIREON IS

• A validation runtime.
• A research framework.
• A plugin ecosystem.
• A benchmarking platform.

VIREON IS NOT

• A replacement for implant firmware.
• A cycle-accurate hardware emulator.
• A medical device.
• A clinical decision system.
• A proprietary device simulator.

1. Stakeholders

Identify all intended users.

Examples:

• Academic researchers
• Security researchers
• Medical-device manufacturers
• Neurotechnology companies
• Universities
• Regulatory researchers

Describe what each stakeholder gains.

1. Assumptions

Explicitly identify every architectural assumption.

Classify each as:

Acceptable

Needs validation

Future work

Unacceptable

Replace implicit assumptions (such as "attacker already has shell") with explicit capability-based assumptions.

1. Design Philosophy

Explain the philosophy behind:

runtime

providers

plugins

validation

simulation

digital twins

benchmarking

Do not discuss implementation.

1. Long-Term Architecture

Describe the ideal architecture five years from now.

Do not reference today's repository.

Describe the destination.

1. Non-Goals

List things that VIREON should intentionally never attempt.

Prevent scope creep.

1. Success Criteria

How would we know VIREON succeeded?

Examples:

• Vendors can integrate proprietary plugins without modifying the framework.
• Researchers can reproduce validation results.
• New devices can be added without changing the runtime.
• New languages can be integrated through stable interfaces.
• The educational platform can evolve independently.

1. Architectural Risks

Identify:

• technical risks
• organisational risks
• maintenance risks
• adoption risks
• scientific risks

Rank by severity.

1. Guiding Question

Finish the document by answering:

"If every line of code disappeared tomorrow, what architectural ideas would still make VIREON worth rebuilding?"

----------------------------------------------------

CRITICAL INSTRUCTIONS
----------------------------------------------------

Do NOT redesign code.

Do NOT generate interfaces.

Do NOT discuss implementation.

Do NOT optimize existing modules.

Do NOT attempt refactoring.

Remain at the level of architecture and systems thinking.

Challenge every assumption.

Reject unnecessary complexity.

Prefer long-term maintainability over feature richness.

If the current vision appears internally inconsistent, explain why and propose a more coherent direction.

The goal is not to justify the current project.

The goal is to determine what VIREON should fundamentally become.

# PHASE 1 — Architecture Extraction

```text
Analyze the entire repository.

Produce a complete architecture document.

Do NOT modify any code.

Identify:

• all modules
• dependencies
• subsystem boundaries
• God classes
• circular dependencies
• extension points
• plugin mechanisms
• runtime lifecycle
• execution flow
• ownership boundaries

Generate:

ARCHITECTURE.md

Include diagrams (Mermaid).

Conclude with:

• strengths
• weaknesses
• technical debt
• architectural risks

Do not propose fixes yet.
```

---

# PHASE 2 — Runtime Redesign

```text
Using the architecture document, redesign only the runtime.

Goal:

Transform the current coordinator into a thin orchestration runtime.

The runtime should know nothing about concrete implementations.

Instead it should interact only through provider interfaces.

Deliverables:

• runtime responsibilities
• lifecycle
• dependency graph
• event flow
• state machine
• capability resolution

Generate diagrams.

Do NOT implement.

Wait for approval.
```

---

# PHASE 3 — Plugin SDK

```text
Design a unified Plugin SDK.

Replace every existing extension mechanism with one provider-based architecture.

Everything should become a provider:

Firmware

Protocol

Threat Model

IDS

Telemetry

Signal Processing

Battery

Safety

Decoder

Benchmark

Reporting

Simulation

Validation

Scenario

Attack

Each provider must define:

• responsibilities
• lifecycle
• interfaces
• versioning
• dependency rules

Generate SDK documentation.

Do not implement.
```

---

# PHASE 4 — Capability System

```text
Design the capability system.

The runtime should discover providers automatically.

Design:

Capability Manifest

Capability Resolution

Dependency Injection

Version Compatibility

Feature Negotiation

Runtime Validation

Plugin Discovery

Plugin Registry

Produce examples.

Do not modify code.
```

---

# PHASE 5 — Security Architecture

```text
Review only security.

Analyze:

NeuroDSL

Plugin Loading

Sandboxing

IPC

Privilege Boundaries

Threat Levels

Scenario Execution

Replace implicit assumptions with explicit attacker capabilities.

Design secure execution.

Produce SECURITY_ARCHITECTURE.md

No implementation.
```

---

# PHASE 6 — Language Independence

```text
Design language-independent execution.

Determine where:

Python

Rust

C

C++

WASM

QEMU

gRPC

FFI

IPC

belong.

The framework must not depend on Python plugins.

Instead define language-neutral contracts.

Generate:

LANGUAGE_ARCHITECTURE.md

Do not implement.
```

---

# PHASE 7 — Simulation Fidelity

```text
Audit simulation fidelity.

Classify every subsystem:

Accurate

Approximate

Abstract

Impossible

Determine:

What should remain simulated.

What should become interfaces.

What vendors should provide.

Generate:

FIDELITY_MATRIX.md

Do not modify code.
```

---

# PHASE 8 — Vendor SDK

```text
Design the Vendor SDK.

Assume:

Neuralink

Synchron

Medtronic

Abbott

will integrate proprietary components.

Design:

Firmware Provider

Decoder Provider

Telemetry Provider

Protocol Provider

Safety Provider

Threat Model Provider

Validation Provider

Capability Manifest

Configuration

Example Plugin

Generate:

VENDOR_SDK.md

No implementation.
```

---

# PHASE 9 — Refactoring

```text
Implement the approved architecture.

Rules:

Small commits.

One subsystem at a time.

Maintain tests.

Maintain compatibility.

After each completed subsystem:

Generate

CHANGELOG

Migration Guide

Architecture Decision Record

Stop before beginning the next subsystem.
```

---

# PHASE 10 — Final Audit

```text
Perform a complete architectural audit.

Review:

Maintainability

Modularity

Coupling

Plugin Architecture

Performance

Security

Research Value

Industry Adoption

Scientific Validity

Score every subsystem.

Recommend future work for:

Version 2

Version 3

Version 5

Produce:

FINAL_ARCHITECTURE_AUDIT.md
```

---
