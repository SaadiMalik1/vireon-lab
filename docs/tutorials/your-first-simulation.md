# Tutorial 1: Your First Simulation

Welcome to VIREON! In this tutorial, you will run a basic headless simulation.

## Prerequisites
Ensure you have installed VIREON (`pip install -e .[all]`).

## Running the Simulation
Open your terminal and run:
```bash
vireon run --duration 15.0 --board synthetic
```
This will start a 15-second simulation using synthetic EEG data.

## Checking the Output
Once the simulation finishes, check the current directory for the generated PDF report. It will contain details of the simulation, battery usage, and any triggered alerts.
