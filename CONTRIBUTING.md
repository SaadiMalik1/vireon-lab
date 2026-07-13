# Contributing to NeuroShield

**Audience**: Developers, Security Researchers, Academic Researchers

First off, thank you for considering contributing to NeuroShield! It's people like you that make NeuroShield such a great platform for neurosecurity research.

## Purpose
This document outlines the process for contributing to the NeuroShield project, including coding standards, branch management, and how to submit pull requests.

## Scope
These guidelines cover all contributions to the NeuroShield repository, including code (core engine, plugins, attacks), documentation, and dataset configurations.

## Prerequisites
- Python 3.10+
- Rust toolchain (for Runemate development)
- Git

## How Can I Contribute?

### Reporting Bugs
This section guides you through submitting a bug report. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.
- Use the GitHub Issue Tracker.
- Provide a clear and descriptive title.
- Describe the exact steps to reproduce the problem.
- Describe the behavior you observed after following the steps and point out exactly what the problem is.

### Suggesting Enhancements
- Use the GitHub Issue Tracker.
- Provide a clear and descriptive title.
- Provide a step-by-step description of the suggested enhancement in as many details as possible.
- Explain why this enhancement would be useful to most NeuroShield users or neurosecurity researchers.

### Pull Requests
1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests to the `tests/` directory.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes (`pytest tests/`).
5. Ensure your code passes the linters (`ruff check .`).
6. Issue that pull request!

## Coding Standards
- We follow PEP 8 standards. Use `ruff` for linting.
- All public methods must include docstrings detailing Purpose, Parameters, Return values, Exceptions, and Security considerations.
- Type hints are required for all new Python code.

## Architecture Principles
NeuroShield uses an event-driven plugin architecture. Do not tightly couple components. Use the `EventBus` for cross-component communication, and the `PluginRegistry` for adding new devices or attack vectors.

## Related Documents
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Architecture Overview](docs/architecture.md)
- [Security Policy](SECURITY.md)
