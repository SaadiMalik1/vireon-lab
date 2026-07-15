// std required for pyo3

pub mod interpreter;
pub mod memory;
pub mod error;

pub fn execute_bytecode(bytecode: &[u8]) -> Result<(), error::ScribeError> {
    let mut ctx = interpreter::ScribeContext::new();
    ctx.execute(bytecode, &[])
}
