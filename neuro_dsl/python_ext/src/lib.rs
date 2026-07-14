use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyRuntimeError};
use scribe::interpreter::ScribeContext;

#[pyclass]
pub struct PyScribe {
    inner: ScribeContext,
    bytecode: Vec<u8>,
}

#[pymethods]
impl PyScribe {
    #[new]
    pub fn new() -> Self {
        PyScribe {
            inner: ScribeContext::new(),
            bytecode: Vec::new(),
        }
    }

    pub fn load_bytecode(&mut self, bytecode: &[u8]) -> PyResult<()> {
        self.bytecode = bytecode.to_vec();
        Ok(())
    }

    pub fn execute_step(&mut self, eeg_data: Vec<f32>) -> PyResult<Vec<f32>> {
        if self.bytecode.is_empty() {
            return Ok(eeg_data);
        }

        if let Err(e) = self.inner.execute(&self.bytecode) {
            return Err(PyRuntimeError::new_err(format!("Scribe execution error: {:?}", e)));
        }

        Ok(eeg_data)
    }
}

/// Compiles a NeuroDSL script string into bytecode.
#[pyfunction]
fn compile_script(source: &str) -> PyResult<Vec<u8>> {
    match forge::compile(source) {
        Ok(bytecode) => Ok(bytecode),
        Err(e) => Err(PyValueError::new_err(format!("Compile error: {:?}", e))),
    }
}

#[pymodule]
fn vireon_neuro_dsl(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyScribe>()?;
    m.add_function(wrap_pyfunction!(compile_script, m)?)?;
    Ok(())
}
