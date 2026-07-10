use crate::ast::{Ast, Statement, ShapeType};
use crate::error::ForgeError;

pub fn generate(ast: Ast) -> Result<Vec<u8>, ForgeError> {
    let mut bytecode = Vec::new();
    
    for stmt in ast.statements {
        match stmt {
            Statement::SetAmp(val) => {
                bytecode.push(0x01);
                bytecode.push(val);
            },
            Statement::SetFreq(val) => {
                bytecode.push(0x02);
                let bytes = val.to_be_bytes();
                bytecode.push(bytes[0]);
                bytecode.push(bytes[1]);
            },
            Statement::Shape(shape_type, size) => {
                bytecode.push(0x03);
                bytecode.push(match shape_type {
                    ShapeType::Circle => 0x10,
                    ShapeType::Square => 0x20,
                    ShapeType::Triangle => 0x30,
                });
                bytecode.push(size);
            },
            Statement::Wait(val) => {
                bytecode.push(0x04);
                let bytes = val.to_be_bytes();
                bytecode.push(bytes[0]);
                bytecode.push(bytes[1]);
            },
            Statement::End => {
                bytecode.push(0xFF);
            }
        }
    }
    
    Ok(bytecode)
}
