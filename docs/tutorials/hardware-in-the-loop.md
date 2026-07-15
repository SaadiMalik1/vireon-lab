# Tutorial 4: Hardware in the Loop (HIL)

VIREON can stream data to and from real physical hardware like OpenBCI boards.

## 1. Connecting the Board
Ensure your OpenBCI Cyton board is plugged in via the USB dongle.

## 2. Running with HIL
Run the simulation and point it to the serial port:
```bash
vireon run --board cyton --serial-port /dev/ttyUSB0
```
*(On Windows, use `--serial-port COM3`)*

## 3. Emulating Telemetry
VIREON will now pull real live EEG data from the board into the Digital Twin for threat evaluation.
