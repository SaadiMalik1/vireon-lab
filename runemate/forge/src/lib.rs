pub mod lexer;
pub mod parser;
pub mod ast;
pub mod codegen;
pub mod disasm;
pub mod secure;
pub mod tara;
pub mod error;

pub fn compile(source: &str) -> Result<Vec<u8>, error::ForgeError> {
    // Pipeline: Lex -> Parse -> Tara Check -> Codegen -> Secure
    Ok(vec![])
}
