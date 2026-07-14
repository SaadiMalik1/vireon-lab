"""
VIREON LSL Receiver Example

This script demonstrates how an external frontend (like OpenBCI GUI, OpenViBE, 
or a custom Python notebook) can subscribe to the VIREON Replay Engine 
via the Lab Streaming Layer (LSL).

Usage:
1. Start VIREON in LSL mode:
   python -m vireon web --lsl

2. Run this receiver:
   python examples/lsl_receiver.py
"""

import json
try:
    from pylsl import resolve_byprop, StreamInlet
except ImportError:
    print("Please install pylsl: pip install pylsl")
    exit(1)

def main():
    print("Looking for VIREON LSL streams...")
    
    # Resolve the EEG/LFP data stream
    eeg_streams = resolve_byprop('name', 'NeuroShield_EEG')
    if not eeg_streams:
        print("Could not find NeuroShield_EEG stream.")
        return
        
    eeg_inlet = StreamInlet(eeg_streams[0])
    
    # Resolve the Telemetry/Security stream
    telemetry_streams = resolve_byprop('name', 'NeuroShield_Telemetry')
    if not telemetry_streams:
        print("Could not find NeuroShield_Telemetry stream.")
        return
        
    telemetry_inlet = StreamInlet(telemetry_streams[0])
    
    print("Connected to VIREON! Listening for data...")
    
    try:
        while True:
            # Check for new telemetry (security markers, IDS confidence, etc.)
            marker, timestamp = telemetry_inlet.pull_sample(timeout=0.0)
            if marker:
                data = json.loads(marker[0])
                msg = f"\n[TELEMETRY] Sim Clock: {data.get('sim_clock', 0):.2f}s | " \
                      f"State: {data.get('hazard_state')} | " \
                      f"Temp: {data.get('temperature_celsius', 37.0):.1f}°C | " \
                      f"Attack: {data.get('active_attack')}"
                
                if "threat_intel" in data:
                    intel = data["threat_intel"]
                    msg += f"\n  ↳ [STIX] {intel.get('stix_id')} - {intel.get('name')}"
                
                print(msg)
            
            # Pull EEG chunks
            chunk, timestamps = eeg_inlet.pull_chunk(timeout=0.1)
            if chunk:
                # In a real app like OpenBCI GUI or BrainFlow, this data 
                # is routed directly to the plotting/DSP pipeline.
                print(f"[EEG] Received chunk of {len(chunk)} samples. Ch0 = {chunk[0][0]:.2f} µV", end="\r")
                
    except KeyboardInterrupt:
        print("\nDisconnected.")

if __name__ == '__main__':
    main()
