"""
Companion App Stub.
Simulates a patient mobile application connecting via BLE.
WARNING: This is a simulation stub.
"""
from typing import Any

class CompanionAppStub:
    def __init__(self, twin: Any):
        self.twin = twin
    
    def start(self):
        print("[CompanionAppStub] Companion App connected via BLE.")
        
    def stop(self):
        print("[CompanionAppStub] Companion App disconnected.")
