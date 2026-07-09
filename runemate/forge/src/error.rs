#[derive(Debug)]
pub enum ForgeError {
    LexerError(String),
    ParseError(String),
    TaraViolation(String),
    SecureEncodingError(String),
}
