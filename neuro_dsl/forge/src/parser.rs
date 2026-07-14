use crate::lexer::Token;
use crate::ast::{Ast, Statement, ShapeType};
use crate::error::ForgeError;

pub fn parse(tokens: Vec<Token>) -> Result<Ast, ForgeError> {
    let mut statements = Vec::new();
    let mut iter = tokens.into_iter().peekable();
    
    while let Some(token) = iter.next() {
        match token {
            Token::SetAmp => {
                if let Some(Token::Number(val)) = iter.next() {
                    statements.push(Statement::SetAmp(val as u8));
                } else {
                    return Err(ForgeError::ParserError("Expected number after SET_AMP".into()));
                }
            },
            Token::SetFreq => {
                if let Some(Token::Number(val)) = iter.next() {
                    statements.push(Statement::SetFreq(val));
                } else {
                    return Err(ForgeError::ParserError("Expected number after SET_FREQ".into()));
                }
            },
            Token::Wait => {
                if let Some(Token::Number(val)) = iter.next() {
                    statements.push(Statement::Wait(val));
                } else {
                    return Err(ForgeError::ParserError("Expected number after WAIT".into()));
                }
            },
            Token::Shape => {
                if let Some(Token::Identifier(shape_name)) = iter.next() {
                    let shape = match shape_name.to_uppercase().as_str() {
                        "CIRCLE" => ShapeType::Circle,
                        "SQUARE" => ShapeType::Square,
                        "TRIANGLE" => ShapeType::Triangle,
                        _ => return Err(ForgeError::ParserError(format!("Unknown shape: {}", shape_name))),
                    };
                    if let Some(Token::Number(size)) = iter.next() {
                        statements.push(Statement::Shape(shape, size as u8));
                    } else {
                        return Err(ForgeError::ParserError("Expected size number after shape name".into()));
                    }
                } else {
                    return Err(ForgeError::ParserError("Expected shape name after SHAPE".into()));
                }
            },
            Token::End => {
                statements.push(Statement::End);
            },
            Token::ReadSensor => {
                if let (Some(Token::Number(sensor)), Some(Token::Number(addr))) = (iter.next(), iter.next()) {
                    statements.push(Statement::ReadSensor(sensor as u8, addr as u8));
                } else {
                    return Err(ForgeError::ParserError("Expected sensor and address after READ_SENSOR".into()));
                }
            },
            Token::LoopStart => {
                if let Some(Token::Number(iters)) = iter.next() {
                    statements.push(Statement::LoopStart(iters as u8));
                } else {
                    return Err(ForgeError::ParserError("Expected iterations after LOOP_START".into()));
                }
            },
            Token::LoopEnd => {
                statements.push(Statement::LoopEnd);
            },
            Token::JumpIf => {
                if let (Some(Token::Number(addr)), Some(Token::Number(val)), Some(Token::Number(target))) = (iter.next(), iter.next(), iter.next()) {
                    statements.push(Statement::JumpIf(addr as u8, val as u8, target as u16));
                } else {
                    return Err(ForgeError::ParserError("Expected address, value, and target after JUMP_IF".into()));
                }
            },
            _ => {
                return Err(ForgeError::ParserError(format!("Unexpected token: {:?}", token)));
            }
        }
    }
    
    Ok(Ast { statements })
}
