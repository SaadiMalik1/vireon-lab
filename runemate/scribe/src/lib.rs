#![no_std]

pub mod interpreter;
pub mod memory;
pub mod error;

pub fn execute_bytecode(bytecode: &[u8]) -> Result<(), error::ScribeError> {
    // Scribe execution engine entry point
    Ok(())
}
