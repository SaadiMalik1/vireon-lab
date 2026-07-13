use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyRuntimeError};
use scribe::interpreter::Scribe;
use scribe::isa::Opcode;

#[pyclass]
pub struct PyScribe {
    inner: Scribe,
}

#[pymethods]
impl PyScribe {
    #[new]
    pub fn new() -> Self {
        PyScribe {
            inner: Scribe::new(),
        }
    }

    pub fn load_bytecode(&mut self, bytecode: &[u8]) -> PyResult<()> {
        match bincode::deserialize::<Vec<Opcode>>(bytecode) {
            Ok(instructions) => {
                self.inner.load(instructions);
                Ok(())
            }
            Err(e) => Err(PyValueError::new_err(format!("Deserialization error: {}", e))),
        }
    }

    pub fn execute_step(&mut self, eeg_data: Vec<f32>) -> PyResult<Vec<f32>> {
        if self.inner.pc >= self.inner.instructions.len() {
            return Ok(eeg_data);
        }

        if let Err(e) = self.inner.step() {
            return Err(PyRuntimeError::new_err(format!("Scribe execution error: {:?}", e)));
        }

        Ok(eeg_data)
    }
}

/// Compiles a Runemate script string into bytecode.
#[pyfunction]
fn compile_script(source: &str) -> PyResult<Vec<u8>> {
    match forge::compile(source) {
        Ok(bytecode) => Ok(bytecode),
        Err(e) => Err(PyValueError::new_err(format!("Compile error: {:?}", e))),
    }
}

#[pymodule]
fn vireon_runemate(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyScribe>()?;
    m.add_function(wrap_pyfunction!(compile_script, m)?)?;
    Ok(())
}
