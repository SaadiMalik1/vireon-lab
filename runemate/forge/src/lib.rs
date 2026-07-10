pub mod lexer;
pub mod parser;
pub mod ast;
pub mod codegen;
pub mod error;

pub fn compile(source: &str) -> Result<Vec<u8>, error::ForgeError> {
    let tokens = lexer::lex(source)?;
    let ast = parser::parse(tokens)?;
    let bytecode = codegen::generate(ast)?;
    Ok(bytecode)
}
