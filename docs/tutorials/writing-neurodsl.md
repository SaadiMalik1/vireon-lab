# Tutorial 5: Writing NeuroDSL

NeuroDSL is a domain-specific language for secure clinical stimulation routines.

## 1. Writing a Script
Create `therapy.rme`:
```text
SET_AMP 2.5
WAIT 100
SET_FREQ 130
```

## 2. Compiling the Script
Use the VIREON CLI to compile the script into secure bytecode using the embedded Rust compiler (`vireon_neuro_dsl`):
```bash
vireon compile therapy.rme -o therapy.bin
```

## 3. Deploying
The `therapy.bin` file can now be loaded into the Digital Twin or sent via an OTA update.
