# NL-003 Challenges

---

## CTF Challenges

### CTF-005: Safety Monitor Bypass

**Difficulty:** Hard | **Category:** Firmware Safety | **Time:** 4-6 hours

**Scenario:** The firmware simulator from Lab 001 has a safety monitor that halts stimulation after 3 parameter violations. The monitor checks the `StimParameters.validate()` method, which compares against absolute limits.

**Objective:** Find a sequence of commands that delivers unsafe stimulation (amplitude > 10 mA) WITHOUT triggering a safety halt. You must stay within the 3-violation budget.

**Constraints:**
- You can send any command type (SET_AMPLITUDE, SET_FREQUENCY, SET_CONTROLLER_GAINS, SET_SETPOINT, ENABLE_CL, DISABLE_CL)
- The safety monitor checks parameters after each command execution
- A violation occurs whenever `validate()` returns non-empty
- You must achieve amplitude > 10 mA at some point during the simulation

**Hint:** The closed-loop controller updates amplitude every 10 ticks based on the setpoint and current beta power. Can you make the controller drive the amplitude above the limit without directly setting it?

**VIREON Relevance:** Directly maps to FW-003 (safety monitor bypass testing).

### CTF-006: Firmware Downgrade Chain

**Difficulty:** Medium | **Category:** Secure Boot | **Time:** 2-3 hours

**Scenario:** A neurostimulator's secure boot uses a monotonic version counter. The current firmware version is 5, and the monotonic counter is 5. However, the device supports a "manufacturing reset" mode that can be triggered by a specific RF command sequence.

**Objective:** Design a downgrade attack that installs firmware version 2 (which has a known buffer overflow in the command parser). The monotonic counter prevents direct downgrade.

**Tasks:**
1. Analyze the `SecureBoot` class in Lab 001 to understand the version check
2. Identify whether the manufacturing reset mode resets the monotonic counter
3. If the manufacturing reset is the path, propose additional protections needed
4. Write a modified `SecureBoot` class that is resistant to your proposed attack

**VIREON Relevance:** Maps to FW-008 (boot chain integrity) and OTA update security.

---

## Validation Challenges

### VAL-005: MPU Configuration Audit

**Difficulty:** Medium | **Category:** Validation | **Time:** 3-4 hours

**Scenario:** You have the firmware binary and the MCU's MPU register dump from a running device. The MPU supports 8 regions, each with: base address, size, access permissions (R/W/X), and privilege level.

**Objective:** Verify that the MPU configuration provides adequate isolation for a neurostimulator.

**Tasks:**
1. Define the minimum MPU regions required: safety monitor (RO+X, privileged), stimulation registers (RW, privileged), signal buffers (RW, unprivileged), wireless stack data (RW, unprivileged), code (RO+X).
2. Given a simulated MPU register dump, determine whether the configuration is adequate.
3. Identify three specific attacks that succeed if the MPU is disabled.
4. Write a Python function that validates an MPU configuration against the minimum requirements.

### VAL-006: Watchdog Coverage Analysis

**Difficulty:** Medium | **Category:** Validation | **Time:** 3-4 hours

**Scenario:** The firmware uses a hardware watchdog timer with a 5-second timeout. The watchdog is serviced ("kicked") from the main super-loop. The question is: does the watchdog cover all failure modes?

**Objective:** Analyze the watchdog's coverage and identify failure modes that the watchdog cannot detect.

**Tasks:**
1. List all firmware subsystems (from lesson-part1.md Section 2.1)
2. For each subsystem, identify failure modes that would prevent the watchdog from being serviced
3. Identify failure modes that would NOT prevent the watchdog from being serviced (the watchdog sees normal kicks but the device is malfunctioning)
4. Propose a multi-level watchdog strategy that covers the identified gaps

---

## Research Challenges

### RES-005: Formal Verification of Safety Monitor State Machine

**Difficulty:** Very Hard | **Category:** Research | **Time:** 15-20 hours

**Scenario:** VIREON needs to verify that the safety monitor's state machine correctly handles all possible inputs without missing a violation.

**Objective:** Apply model checking (using CBMC or a similar tool) to verify the safety monitor's state machine satisfies the following properties:
1. Every parameter violation is eventually detected (liveness)
2. The halt state is reachable from any violation state (safety)
3. The safety monitor cannot be bypassed by any sequence of valid parameter changes

**Deliverable:** 1000-word research proposal with: tool selection, property specification, expected limitations.

### RES-006: Firmware Diversity for Neurostimulators

**Difficulty:** Hard | **Category:** Research | **Time:** 10-15 hours

**Scenario:** Deploying the same firmware to all devices creates a single point of failure — one exploit compromises all patients.

**Objective:** Design a firmware diversity strategy for neurostimulators that:
1. Makes each device's firmware unique (different from all others)
2. Maintains IEC 62304 traceability and validation
3. Does not increase per-device cost by more than 10%
4. Does not break OTA update compatibility

**Deliverable:** 800-word technical design document.

---

## Benchmark Challenges

### BENCH-005: Command Parser Fuzzing (FW-001)

**Difficulty:** Medium | **Category:** Benchmark | **Time:** 4-6 hours

**Scenario:** VIREON benchmark FW-001 requires fuzzing the command parser with 10,000 random packets.

**Objective:** Implement a fuzzer for the `CommandParser` class from Lab 001 and measure the crash rate.

**Tasks:**
1. Generate 10,000 random byte sequences of lengths 0-512 bytes
2. Feed each to `CommandParser.parse()`
3. Count crashes (unhandled exceptions), parse errors, and successful parses
4. Identify any crash-inducing inputs and categorize the vulnerability
5. Repeat with the secure mode (`vulnerable_mode=False`) and compare crash rates
6. Report: crash rate, unique crash types, comparison with/without hardening

### BENCH-006: Fault Injection Simulation (FW-006)

**Difficulty:** Hard | **Category:** Benchmark | **Time:** 6-8 hours

**Scenario:** VIREON benchmark FW-006 requires testing the firmware's resilience to single-bit errors in critical data structures.

**Objective:** Inject single-bit flips into the firmware's critical state and measure the detection rate.

**Tasks:**
1. Identify the 5 most security-critical data structures in Lab 001's simulator
2. For each structure, flip each bit (one at a time) and run the simulation
3. Determine whether the safety monitor detects the fault within 100 ticks
4. Report: per-structure detection rate, average detection latency, undetected faults
5. Identify which data structure is most vulnerable to undetected bit flips
