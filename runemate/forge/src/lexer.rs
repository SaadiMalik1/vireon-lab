use crate::error::ForgeError;

#[derive(Debug, PartialEq, Clone)]
pub enum Token {
    SetAmp,
    SetFreq,
    Shape,
    Wait,
    End,
    Number(u16),
    Identifier(String),
}

pub fn lex(source: &str) -> Result<Vec<Token>, ForgeError> {
    let mut tokens = Vec::new();
    let words = source.split_whitespace();
    
    for word in words {
        let token = match word.to_uppercase().as_str() {
            "SET_AMP" => Token::SetAmp,
            "SET_FREQ" => Token::SetFreq,
            "SHAPE" => Token::Shape,
            "WAIT" => Token::Wait,
            "END" => Token::End,
            _ => {
                if let Ok(num) = word.parse::<u16>() {
                    Token::Number(num)
                } else {
                    Token::Identifier(word.to_string())
                }
            }
        };
        tokens.push(token);
    }
    
    Ok(tokens)
}
