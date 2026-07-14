use std::io::{self, Read};
use forge::compile;

fn main() {
    let mut source = String::new();
    if let Err(e) = io::stdin().read_to_string(&mut source) {
        eprintln!("Error reading stdin: {}", e);
        std::process::exit(1);
    }

    match compile(&source) {
        Ok(bytecode) => {
            let hex: String = bytecode.iter().map(|b| format!("{:02X}", b)).collect();
            println!("{}", hex);
        }
        Err(e) => {
            eprintln!("Compilation failed: {:?}", e);
            std::process::exit(1);
        }
    }
}
