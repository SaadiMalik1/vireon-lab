pub enum ScribeError {
    InvalidOpcode(u8),
    StackOverflow,
    StackUnderflow,
    MemoryOutOfBounds,
    NeurowallViolation,
}
