#[derive(Debug, PartialEq)]
pub enum ShapeType {
    Circle,
    Square,
    Triangle,
}

#[derive(Debug, PartialEq)]
pub enum Statement {
    SetAmp(u8),
    SetFreq(u16),
    Shape(ShapeType, u8),
    Wait(u16),
    End,
}

#[derive(Debug)]
pub struct Ast {
    pub statements: Vec<Statement>,
}
