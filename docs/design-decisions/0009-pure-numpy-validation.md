# ADR 0009: Pure NumPy, Dependency-Free Validation Architecture

## Status
Accepted

## Context
Processing EEG data normally relies heavily on comprehensive scientific libraries like `MNE-Python` or `SciPy` for filtering, spectral analysis, and file parsing. In a purely clinical or data-science context, importing these massive dependency chains is standard practice.

However, VIREON operates in the intersection of embedded systems security and neuroscience. If we require gigabytes of dependencies to validate an anomaly detection engine, it becomes impossible to deploy the validation logic onto constrained hardware-in-the-loop (HIL) environments or lightweight Docker containers for continuous integration. Furthermore, complex abstraction layers in libraries like MNE obscure the fundamental mathematics behind the security validation.

## Decision
We explicitly chose to build the core validation and detection engine using **only the Python standard library and NumPy**.

1. **Custom EDF Parser**: We wrote a lightweight, pure-Python `.edf` ingestion module tailored exclusively for continuous streaming simulation, stripping out clinical metadata handling we do not need.
2. **NumPy Math**: All spectral analysis (FFT), windowing, EWMA, and statistical generation (ROC-AUC approximations, Confidence Intervals) are executed directly using raw NumPy array operations.

## Consequences

### Positive
- **Extreme Portability**: The entire validation suite can be deployed almost anywhere instantly, completely avoiding the dependency hell typically associated with neuroscience pipelines.
- **Transparency**: Security researchers can audit the exact mathematical transformations applied to the signal array, block by block, without digging into third-party library source code.
- **Performance**: Operating directly on continuous memory arrays with minimal overhead allows the validation runner to process hours of EEG data in milliseconds.

### Negative
- **Reinventing the Wheel**: We are forced to manually maintain code (like the EDF reader and specific filtering logic) that has already been perfected by the open-source community elsewhere.
- **Feature Limitation**: We lack access to out-of-the-box advanced artifact rejection (ICA, Maxwell filtering) provided by standard libraries, requiring us to simulate them manually if needed.
