use crate::ast::{Ast, Statement};
use crate::error::ForgeError;

pub fn verify_ast(ast: &Ast) -> Result<(), ForgeError> {
    let mut loop_depth = 0;
    
    for stmt in &ast.statements {
        match stmt {
            Statement::SetAmp(val) => {
                // Example guardrail: Amplitude should not exceed safety limits
                if *val > 100 {
                    return Err(ForgeError::ParserError(format!("Amplitude {} exceeds safety limit of 100", val)));
                }
            },
            Statement::SetFreq(val) => {
                // Example guardrail: Frequency bounds (e.g., must be <= 1000 Hz)
                if *val > 1000 {
                    return Err(ForgeError::ParserError(format!("Frequency {} exceeds safety limit of 1000Hz", val)));
                }
            },
            Statement::LoopStart(iters) => {
                // Limit maximum iterations per loop to prevent runaway
                if *iters > 100 {
                    return Err(ForgeError::ParserError(format!("Loop iterations {} exceeds limit of 100", iters)));
                }
                loop_depth += 1;
                // Limit nested loops to depth 3
                if loop_depth > 3 {
                    return Err(ForgeError::ParserError("Exceeded maximum loop nesting depth of 3".to_string()));
                }
            },
            Statement::LoopEnd => {
                if loop_depth == 0 {
                    return Err(ForgeError::ParserError("Unmatched LOOP_END statement".to_string()));
                }
                loop_depth -= 1;
            },
            Statement::JumpIf(_, _, target) => {
                // Since target is currently an absolute offset and can't easily be validated at AST level
                // (before codegen sizes are known), we just do a rudimentary check. 
                // A better approach would be to calculate bytecode size per statement.
                // For now, limit jump targets to reasonable boundaries.
                if *target > 4096 {
                    return Err(ForgeError::ParserError(format!("JUMP_IF target {} is out of realistic program bounds", target)));
                }
            },
            _ => {}
        }
    }
    
    if loop_depth != 0 {
        return Err(ForgeError::ParserError("Unmatched LOOP_START statement at end of program".to_string()));
    }
    
    Ok(())
}
