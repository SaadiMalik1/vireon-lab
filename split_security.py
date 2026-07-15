import re

with open('/home/ronin/Documents/n2/vireon/core/security.py', 'r') as f:
    content = f.read()

# We need to split into detection.py and clinical.py
neuroips_match = re.search(r'class NeuroIPS:', content)
if not neuroips_match:
    print("Could not find NeuroIPS")
    exit(1)

neuroips_start = neuroips_match.start()

detection_content = content[:neuroips_start]
clinical_content = content[neuroips_start:]

detection_imports = """import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import os
import logging
import threading
import importlib.resources as pkg_resources

from vireon.core.twin import DigitalTwin
from vireon.core.event_bus import EventBus, Event
from vireon.core.threat_intel import ThreatIntelligence
from vireon.core.utils import calculate_rms

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
"""

# Replace the top imports in detection_content
detection_content = re.sub(r'import numpy as np.*?TORCH_AVAILABLE = False\n', '', detection_content, flags=re.DOTALL)
detection_content = detection_imports + "\n" + detection_content

# Add locks to SecurityEngine
detection_content = detection_content.replace(
    'self.threat_intel = ThreatIntelligence(registry_path)',
    'self.threat_intel = ThreatIntelligence(registry_path)\n        self._lock = threading.RLock()'
)

# Add lock to analyze_signal
detection_content = detection_content.replace(
    'def analyze_signal(self, data: np.ndarray) -> List[str]:\n',
    'def analyze_signal(self, data: np.ndarray) -> List[str]:\n        with self._lock:\n            return self._analyze_signal(data)\n\n    def _analyze_signal(self, data: np.ndarray) -> List[str]:\n'
)

# Add lock to analyze_commands
detection_content = detection_content.replace(
    'def analyze_commands(self, amplitude: float, frequency: float) -> List[str]:\n',
    'def analyze_commands(self, amplitude: float, frequency: float) -> List[str]:\n        with self._lock:\n            return self._analyze_commands(amplitude, frequency)\n\n    def _analyze_commands(self, amplitude: float, frequency: float) -> List[str]:\n'
)

# Add lock to analyze_clinical
detection_content = detection_content.replace(
    'def analyze_clinical(self, current_beta_power: float, stim_enabled: bool, amplitude: float) -> List[str]:\n',
    'def analyze_clinical(self, current_beta_power: float, stim_enabled: bool, amplitude: float) -> List[str]:\n        with self._lock:\n            return self._analyze_clinical(current_beta_power, stim_enabled, amplitude)\n\n    def _analyze_clinical(self, current_beta_power: float, stim_enabled: bool, amplitude: float) -> List[str]:\n'
)

clinical_imports = """import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import math
import threading

from vireon.core.twin import DigitalTwin
from vireon.core.event_bus import EventBus, Event
from vireon.core.safety_envelope import SafetyEnvelope
from vireon.core.utils import calculate_rms
from vireon.core.detection import SecurityEngine

"""
clinical_content = clinical_imports + clinical_content

# Add locks to NeuroIPS
clinical_content = clinical_content.replace(
    'self.safety_envelope = SafetyEnvelope(max_amplitude_ma=max_stimulation_amplitude_ma)',
    'self.safety_envelope = SafetyEnvelope(max_amplitude_ma=max_stimulation_amplitude_ma)\n        self._lock = threading.RLock()'
)
clinical_content = clinical_content.replace(
    'def sanitize_stimulation_write(self, amplitude: float, frequency: float) -> Tuple[float, float]:\n',
    'def sanitize_stimulation_write(self, amplitude: float, frequency: float) -> Tuple[float, float]:\n        with self._lock:\n            return self._sanitize_stimulation_write(amplitude, frequency)\n\n    def _sanitize_stimulation_write(self, amplitude: float, frequency: float) -> Tuple[float, float]:\n'
)
clinical_content = clinical_content.replace('        import math\n', '')
clinical_content = clinical_content.replace(
    'def mitigate_signal_anomalies(self, data: np.ndarray, anomalies: List[str]) -> np.ndarray:\n',
    'def mitigate_signal_anomalies(self, data: np.ndarray, anomalies: List[str]) -> np.ndarray:\n        with self._lock:\n            return self._mitigate_signal_anomalies(data, anomalies)\n\n    def _mitigate_signal_anomalies(self, data: np.ndarray, anomalies: List[str]) -> np.ndarray:\n'
)
clinical_content = clinical_content.replace(
    'def mitigate_pathological_sync(self, anomalies: List[str]) -> bool:\n',
    'def mitigate_pathological_sync(self, anomalies: List[str]) -> bool:\n        with self._lock:\n            return self._mitigate_pathological_sync(anomalies)\n\n    def _mitigate_pathological_sync(self, anomalies: List[str]) -> bool:\n'
)

clinical_content = clinical_content.replace(
    'self.blocked_spoofing_attempts = 0',
    'self.blocked_spoofing_attempts = 0\n        self._lock = threading.RLock()'
)
clinical_content = clinical_content.replace(
    'def verify_connection(self, client_mac: str, is_paired: bool, bonding_db: dict) -> bool:\n',
    'def verify_connection(self, client_mac: str, is_paired: bool, bonding_db: dict) -> bool:\n        with self._lock:\n            return self._verify_connection(client_mac, is_paired, bonding_db)\n\n    def _verify_connection(self, client_mac: str, is_paired: bool, bonding_db: dict) -> bool:\n'
)
clinical_content = clinical_content.replace(
    'def check_rf_environment(self):\n',
    'def check_rf_environment(self):\n        with self._lock:\n            return self._check_rf_environment()\n\n    def _check_rf_environment(self):\n'
)
clinical_content = clinical_content.replace(
    'def verify_mtu(self, requested_mtu: int) -> int:\n',
    'def verify_mtu(self, requested_mtu: int) -> int:\n        with self._lock:\n            return self._verify_mtu(requested_mtu)\n\n    def _verify_mtu(self, requested_mtu: int) -> int:\n'
)

with open('/home/ronin/Documents/n2/vireon/core/detection.py', 'w') as f:
    f.write(detection_content)

with open('/home/ronin/Documents/n2/vireon/core/clinical.py', 'w') as f:
    f.write(clinical_content)

print("Split completed successfully!")
