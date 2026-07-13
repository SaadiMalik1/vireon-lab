use pyo3::prelude::*;
use pyo3::types::PyBytes;
use crate::interpreter::Scribe;
use crate::isa::Opcode;

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
            Err(e) => Err(pyo3::exceptions::PyValueError::new_err(format!("Deserialization error: {}", e))),
        }
    }

    pub fn execute_step(&mut self, eeg_data: Vec<f32>) -> PyResult<Vec<f32>> {
        // We'll map execute_step directly if we need to.
        // For now, let's just expose a run mechanism that acts on state.
        
        // This is a stub bridging logic: if the python engine passes us the latest block of EEG data,
        // we write it into scribe memory, step, and return the modified state.
        
        if self.inner.pc >= self.inner.instructions.len() {
            // Halted or finished
            return Ok(eeg_data);
        }

        // Just step the interpreter. Real implementation would sync memory spaces here.
        if let Err(e) = self.inner.step() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err(format!("Scribe execution error: {:?}", e)));
        }

        Ok(eeg_data)
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn neuroshield_runemate(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyScribe>()?;
    Ok(())
}
