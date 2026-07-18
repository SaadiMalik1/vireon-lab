# Migration Checklist: Ecosystem Split

This checklist dictates the rigorous, reversible process of splitting the VIREON monolithic repository into the `VIREON` Framework and `VIREON <SUFFIX>` Educational Platform.

## Stage 1: Internal Refactoring
**Goal**: Isolate domain logic before physically moving files.

- [ ] Delete `vireon/core/coordinator.py` (Deprecated).
- [ ] Delete `vireon/core/coordinator_builder.py` (Deprecated).
- [ ] Delete `vireon/core/coordinator_callbacks.py` (Deprecated).
- [ ] Delete `vireon/core/twin.py` (Deprecated).
- [ ] Refactor `dashboard/app.py` to use *only* `vireon.sdk` and `vireon.core.orchestrator` imports.
- [ ] Remove all hardcoded references to `Kuramoto` or `clinical` logic from `vireon/core/engine.py`.
- [ ] Verify `pytest` passes with 100% core isolation.

## Stage 2: Extract Runtime
**Goal**: Prepare the core directory for extraction.

- [ ] Create `VIREON/src/vireon/core/`.
- [ ] Move `orchestrator.py`, `event_bus.py`, `state_store.py`, `plugin_registry.py`, `capability_engine.py` to `VIREON/src/vireon/core/`.
- [ ] Create `VIREON/src/vireon/security/`.
- [ ] Move `authentication.py`, `e2ee.py`, `guardrails.py`, `zta.py` to `VIREON/src/vireon/security/`.
- [ ] Create `VIREON/src/vireon/validation/`.
- [ ] Move `validation.py`, `compliance.py`, `fuzzer.py`, `sbom.py`, `redteam.py`, `threat_intel.py`, `spdf_auditor.py` to `VIREON/src/vireon/validation/`.
- [ ] Move `engine.py` to `VIREON/src/vireon/engine/`.

## Stage 3: Extract SDK
**Goal**: Formalize the public API contract.

- [ ] Create `VIREON/src/vireon/sdk/`.
- [ ] Move `vireon/sdk/` contents into `VIREON/src/vireon/sdk/`.
- [ ] Move `interfaces.py`, `protocol.py`, `data_provider.py` into `VIREON/src/vireon/sdk/`.
- [ ] Update all intra-framework `import` paths.

## Stage 4: Move Educational Content
**Goal**: Populate the new `VIREON <SUFFIX>` repository.

- [ ] Initialize `VIREON_SUFFIX` git repository.
- [ ] Move `vireon/dashboard/` -> `VIREON_SUFFIX/dashboard/`.
- [ ] Move `vireon/attacks/` -> `VIREON_SUFFIX/scenarios/attacks/`.
- [ ] Move `vireon/core/attack/` -> `VIREON_SUFFIX/scenarios/attack_framework/`.
- [ ] Move `vireon/plugins/firmware/` -> `VIREON_SUFFIX/examples/firmware/`.
- [ ] Move `vireon/plugins/clinical/` -> `VIREON_SUFFIX/examples/clinical/`.
- [ ] Move `vireon/plugins/ble/` -> `VIREON_SUFFIX/examples/ble/`.
- [ ] Move `vireon/core/detection.py` -> `VIREON_SUFFIX/examples/ids/`.
- [ ] Move `vireon/core/physics.py` & `vireon/core/dynamics.py` -> `VIREON_SUFFIX/examples/physics/`.
- [ ] Move `vireon/core/ml_decoder.py` -> `VIREON_SUFFIX/examples/decoders/`.
- [ ] Move `vireon/core/reference_credits/` -> `VIREON_SUFFIX/docs/reference/`.
- [ ] Change all imports in `VIREON_SUFFIX` files from relative (`from ..core import`) to external (`import vireon.core`).

## Stage 5: Packaging & Release
**Goal**: Publish the isolated ecosystems.

- [ ] Create `pyproject.toml` for `VIREON` defining the `vireon-core` package.
- [ ] Create `pyproject.toml` for `VIREON <SUFFIX>` defining dependency on `vireon-core == 1.0.0`.
- [ ] Update Github Actions CI for `VIREON` to trigger downstream `VIREON <SUFFIX>` tests.
- [ ] Release `VIREON v1.0.0` to PyPI.
- [ ] Release `VIREON <SUFFIX> v1.0.0`.

## Reversibility
- Until Stage 5 is finalized, all Stage 1-4 changes occur on an integration branch.
- If Stage 4 uncovers tight coupling that was missed, the migration halts, the `VIREON` public SDK is expanded to cover the missing capability, and the migration resumes.
