"""
Cloud Backend Stub.
Simulates a remote cloud backend connecting to the Digital Twin for telemetry syncing.
WARNING: This is a simulation stub. No real cloud connection is established.
"""
from typing import Any

class CloudBackendStub:
    def __init__(self, twin: Any):
        self.twin = twin
    
    def start(self):
        print("[CloudBackendStub] Connected to Cloud Telemetry.")
        
    def stop(self):
        print("[CloudBackendStub] Disconnected from Cloud Telemetry.")
