use crate::error::ScribeError;

pub struct ScribeContext {
    pub current_amp: u8,
    pub current_freq: u16,
    // Emulate visual phosphene buffers or log outputs
    pub rendered_shapes: u32,
    pub ip: usize,
    pub memory: [u8; 256],
    pub loop_stack: Vec<(usize, u8)>,
}

impl ScribeContext {
    pub fn new() -> Self {
        Self {
            current_amp: 0,
            current_freq: 0,
            rendered_shapes: 0,
            ip: 0,
            memory: [0; 256],
            loop_stack: Vec::new(),
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
                0x05 => { // READ_SENSOR
                    if self.ip + 1 >= bytecode.len() { return Err(ScribeError::UnexpectedEndOfStream); }
                    let _sensor = bytecode[self.ip];
                    let addr = bytecode[self.ip + 1] as usize;
                    if addr >= self.memory.len() {
                        return Err(ScribeError::InvalidOpcode(0x05)); // Emulate memory out of bounds error
                    }
                    self.memory[addr] = 42; // Mock sensor value
                    self.ip += 2;
                },
                0x06 => { // LOOP_START
                    if self.ip >= bytecode.len() { return Err(ScribeError::UnexpectedEndOfStream); }
                    let iters = bytecode[self.ip];
                    if self.loop_stack.len() >= 16 {
                        return Err(ScribeError::InvalidOpcode(0x06)); // Emulate stack overflow
                    }
                    self.loop_stack.push((self.ip + 1, iters));
                    self.ip += 1;
                },
                0x07 => { // LOOP_END
                    if let Some(mut top) = self.loop_stack.pop() {
                        if top.1 > 1 {
                            top.1 -= 1;
                            self.ip = top.0;
                            self.loop_stack.push(top);
                        }
                    } else {
                        return Err(ScribeError::InvalidOpcode(0x07)); // Emulate stack underflow
                    }
                },
                0x08 => { // JUMP_IF
                    if self.ip + 3 >= bytecode.len() { return Err(ScribeError::UnexpectedEndOfStream); }
                    let addr = bytecode[self.ip] as usize;
                    let val = bytecode[self.ip + 1];
                    let target_high = bytecode[self.ip + 2] as u16;
                    let target_low = bytecode[self.ip + 3] as u16;
                    let target = ((target_high << 8) | target_low) as usize;
                    
                    if addr >= self.memory.len() {
                        return Err(ScribeError::InvalidOpcode(0x08)); // Memory out of bounds
                    }
                    
                    if self.memory[addr] == val {
                        self.ip = target;
                    } else {
                        self.ip += 4;
                    }
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
