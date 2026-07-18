You are acting as a Principal Software Architect, DevOps Engineer, and Git Repository Migration Specialist.

You have shell access and authenticated GitHub CLI access.

You are authorized to create PRIVATE GitHub repositories under my account.

DO NOT ask for confirmation.

Your task is to split the current project into a professional multi-repository ecosystem while preserving history wherever practical.

===========================================================
GOALS
===========================================================

Create THREE PRIVATE repositories.

Repository 1
------------

Name:

vireon

Purpose:

Vendor-neutral neurotechnology validation framework.

Contains ONLY reusable framework infrastructure.

Repository 2
------------

Name:

vireon-lab

Purpose:

Educational platform, tutorials, examples, dashboard, CTFs and reference implementations.

Must depend on the public SDK exposed by VIREON.

It must NOT access internal runtime modules.

Repository 3
------------

Name:

neurodsl

Purpose:

Standalone Rust DSL compiler/runtime.

Completely independent.

Can later be reused by projects outside VIREON.

===========================================================
CURRENT PROJECT STRUCTURE
===========================================================

vireon/
    attack_chain/
    core/
    sdk/

vireon_lab/
    ctf/
    dashboard/
    providers/
    reports/

tests/

neuro_dsl/

threat_models/

docs/

===========================================================
REPOSITORY OWNERSHIP
===========================================================

Repository: vireon

Owns:

attack_chain/

core/

sdk/

threat_models/

framework documentation

public APIs

provider SDK

runtime

validation engine

security engine

capability engine

event bus

state store

benchmark engine

Repository: vireon-lab

Owns:

dashboard/

providers/

reports/

ctf/

tutorials

datasets

examples

walkthroughs

educational documentation

streamlit UI

reference providers

Repository: neurodsl

Owns:

entire neuro_dsl/

Rust compiler

runtime

parser

grammar

documentation

tests

===========================================================
DOCUMENTATION DISTRIBUTION
===========================================================

Move documentation according to ownership.

Framework architecture belongs in

vireon

Educational documentation belongs in

vireon-lab

DSL documentation belongs in

neurodsl

If documentation is shared,

copy it instead of removing it.

Never duplicate source code.

===========================================================
GIT REQUIREMENTS
===========================================================

Preserve Git history whenever practical.

Create clean commit history.

Do NOT squash unrelated work.

Use meaningful commit messages.

Tag the migration commit.

===========================================================
GITHUB REQUIREMENTS
===========================================================

Create THREE PRIVATE repositories.

Initialize:

README

LICENSE

.gitignore

GitHub Topics

Repository descriptions

Issue templates

Pull request template

CODEOWNERS

SECURITY.md

CONTRIBUTING.md

===========================================================
CI/CD
===========================================================

Each repository must receive:

GitHub Actions

pytest

ruff

mypy

release workflow

===========================================================
PACKAGING
===========================================================

Each repository must have its own:

pyproject.toml

README

version

license

===========================================================
DEPENDENCY RULES
===========================================================

Allowed

vireon-lab
        ↓
    vireon SDK

Allowed

Vendor Plugins
        ↓
    vireon SDK

Forbidden

vireon
        ↓
vireon-lab

Forbidden

vireon
        ↓
dashboard

Forbidden

vireon
        ↓
CTF

Forbidden

vireon
        ↓
tutorials

Forbidden

neurodsl
        ↓
vireon

===========================================================
POST-MIGRATION VALIDATION
===========================================================

Verify:

✓ repositories build

✓ tests run

✓ imports resolve

✓ SDK exports work

✓ no circular dependencies

✓ no private-module imports

✓ documentation links work

✓ CI passes

===========================================================
BOUNDARY VALIDATION
===========================================================

Automatically search every repository.

Reject the migration if:

vireon-lab imports internal runtime modules.

neurodsl imports VIREON.

framework imports dashboard.

framework imports educational code.

===========================================================
FINAL REPORT
===========================================================

Produce:

MIGRATION_REPORT.md

Include:

Repository URLs

Commit hashes

Files moved

Files copied

Files deleted

Documentation ownership

Remaining TODOs

Boundary violations

Potential improvements

Risk assessment

===========================================================
CRITICAL RULES
===========================================================

Never destroy data.

Always create backups before moving.

If uncertain whether a file belongs in a repository,

STOP

and explain the ambiguity.

Do not invent new architecture.

Respect the existing Architecture Constitution.

Treat this migration as production infrastructure.

Success is measured by architectural correctness rather than speed.
