use crate::error::ScribeError;
use std::collections::HashSet;

pub struct ScribeContext {
    pub current_amp: u8,
    pub current_freq: u16,
    // Emulate visual phosphene buffers or log outputs
    pub rendered_shapes: u32,
    pub ip: usize,
    pub memory: [u8; 256],
    pub loop_stack: Vec<(usize, u8)>,
}

impl Default for ScribeContext {
    fn default() -> Self {
        Self::new()
    }
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

    pub fn verify(&self, bytecode: &[u8]) -> Result<(), ScribeError> {
        let mut valid_offsets = HashSet::new();
        let mut ip = 0;
        
        // Pass 1: Build valid offsets and enforce limits
        while ip < bytecode.len() {
            valid_offsets.insert(ip);
            let opcode = bytecode[ip];
            match opcode {
                0x01 => {
                    if ip + 1 >= bytecode.len() { return Err(ScribeError::UnexpectedEndOfStream); }
                    if bytecode[ip + 1] > 100 { return Err(ScribeError::SecurityViolation("Amplitude > 100".into())); }
                    ip += 2;
                },
                0x02 => {
                    if ip + 2 >= bytecode.len() { return Err(ScribeError::UnexpectedEndOfStream); }
                    let freq = ((bytecode[ip + 1] as u16) << 8) | (bytecode[ip + 2] as u16);
                    if freq > 1000 { return Err(ScribeError::SecurityViolation("Frequency > 1000".into())); }
                    ip += 3;
                },
                0x03 => ip += 3,
                0x04 => ip += 3,
                0x05 => ip += 3,
                0x06 => ip += 2,
                0x07 => ip += 1,
                0x08 => ip += 5,
                0xFF => break,
                _ => return Err(ScribeError::InvalidOpcode(opcode)),
            }
        }
        
        // Pass 2: Verify JUMP_IF targets are aligned
        ip = 0;
        while ip < bytecode.len() {
            let opcode = bytecode[ip];
            match opcode {
                0x01 => ip += 2,
                0x02 => ip += 3,
                0x03 => ip += 3,
                0x04 => ip += 3,
                0x05 => ip += 3,
                0x06 => ip += 2,
                0x07 => ip += 1,
                0x08 => {
                    let target_high = bytecode[ip + 3] as u16;
                    let target_low = bytecode[ip + 4] as u16;
                    let target = ((target_high << 8) | target_low) as usize;
                    if !valid_offsets.contains(&target) {
                        return Err(ScribeError::UnalignedJump);
                    }
                    ip += 5;
                },
                0xFF => break,
                _ => return Err(ScribeError::InvalidOpcode(opcode)),
            }
        }
        Ok(())
    }

    pub fn execute(&mut self, bytecode: &[u8], eeg_data: &[f32]) -> Result<(), ScribeError> {
        let mut gas = 10_000;
        while self.ip < bytecode.len() {
            if gas == 0 {
                return Err(ScribeError::OutOfGas);
            }
            gas -= 1;

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
                    self.ip += 2;
                },
                0x05 => { // READ_SENSOR
                    if self.ip + 1 >= bytecode.len() { return Err(ScribeError::UnexpectedEndOfStream); }
                    let sensor = bytecode[self.ip];
                    let addr = bytecode[self.ip + 1] as usize;
                    if addr >= self.memory.len() {
                        return Err(ScribeError::InvalidOpcode(0x05));
                    }
                    if !eeg_data.is_empty() {
                        let val = eeg_data[sensor as usize % eeg_data.len()];
                        // Map -1000..1000 to 0..255
                        let normalized = ((val.clamp(-1000.0, 1000.0) + 1000.0) * (255.0 / 2000.0)) as u8;
                        self.memory[addr] = normalized;
                    } else {
                        self.memory[addr] = 0;
                    }
                    self.ip += 2;
                },
                0x06 => { // LOOP_START
                    if self.ip >= bytecode.len() { return Err(ScribeError::UnexpectedEndOfStream); }
                    let iters = bytecode[self.ip];
                    if self.loop_stack.len() >= 3 { // AST enforces 3
                        return Err(ScribeError::InvalidOpcode(0x06));
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
                        return Err(ScribeError::InvalidOpcode(0x07));
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
                        return Err(ScribeError::InvalidOpcode(0x08));
                    }
                    
                    if target >= bytecode.len() {
                        return Err(ScribeError::InvalidOpcode(0x08));
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
