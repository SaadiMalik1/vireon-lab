use crate::error::ScribeError;

pub struct ScribeContext {
    pub current_amp: u8,
    pub current_freq: u16,
    // Emulate visual phosphene buffers or log outputs
    pub rendered_shapes: u32,
    pub ip: usize,
}

impl ScribeContext {
    pub fn new() -> Self {
        Self {
            current_amp: 0,
            current_freq: 0,
            rendered_shapes: 0,
            ip: 0,
        }
    }

    pub fn execute(&mut self, bytecode: &[u8]) -> Result<(), ScribeError> {
        while self.ip < bytecode.len() {
            let opcode = bytecode[self.ip];
            self.ip += 1;

            match opcode {
                0x01 => { // SET_AMP
                    if self.ip >= bytecode.len() { return Err(ScribeError::UnexpectedEndOfStream); }
                    self.current_amp = bytecode[self.ip];
                    self.ip += 1;
                },
                0x02 => { // SET_FREQ
                    if self.ip + 1 >= bytecode.len() { return Err(ScribeError::UnexpectedEndOfStream); }
                    let high = bytecode[self.ip] as u16;
                    let low = bytecode[self.ip + 1] as u16;
                    self.current_freq = (high << 8) | low;
                    self.ip += 2;
                },
                0x03 => { // SHAPE
                    if self.ip + 1 >= bytecode.len() { return Err(ScribeError::UnexpectedEndOfStream); }
                    let _shape_type = bytecode[self.ip];
                    let _size = bytecode[self.ip + 1];
                    self.rendered_shapes += 1;
                    self.ip += 2;
                },
                0x04 => { // WAIT
                    if self.ip + 1 >= bytecode.len() { return Err(ScribeError::UnexpectedEndOfStream); }
                    let _high = bytecode[self.ip] as u16;
                    let _low = bytecode[self.ip + 1] as u16;
                    // In a no_std embedded environment, wait would interact with hardware timers
                    self.ip += 2;
                },
                0xFF => { // END
                    break;
                },
                _ => return Err(ScribeError::InvalidOpcode(opcode)),
            }
        }
        Ok(())
    }
}
