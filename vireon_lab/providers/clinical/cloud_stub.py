# Copyright 2026 VIREON Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
