#[derive(Debug)]
pub enum ForgeError {
    LexerError(String),
    ParserError(String),
    CodegenError(String),
}
