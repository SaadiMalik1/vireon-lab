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
    ReadSensor(u8, u8),
    LoopStart(u8),
    LoopEnd,
    JumpIf(u8, u8, u16),
}

#[derive(Debug)]
pub struct Ast {
    pub statements: Vec<Statement>,
}
