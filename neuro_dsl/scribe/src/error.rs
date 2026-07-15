#[derive(Debug)]
pub enum ScribeError {
    InvalidOpcode(u8),
    UnexpectedEndOfStream,
    MemoryError,
    OutOfGas,
    UnalignedJump,
    SecurityViolation(String),
}
