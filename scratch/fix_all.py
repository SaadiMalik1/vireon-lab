import sys, re, os

def fix_file(path, replacements):
    if not os.path.exists(path): return
    with open(path, 'r') as f: c = f.read()
    orig = c
    for s, r in replacements: c = c.replace(s, r)
    if c != orig:
        with open(path, 'w') as f: f.write(c)
        print(f"Fixed {path}")

fix_file("vireon/core/coordinator.py", [
    ("import threading\n", ""),
    ("import time\n", ""),
    ("import asyncio\n", ""),
    ("import logging\n", ""),
    ("from typing import List, Dict, Optional, Callable", "from typing import Dict, Optional, Callable"),
    ("logger = logging.getLogger(__name__)\n", ""),
    ("f\"Active Scenarios:\"", "\"Active Scenarios:\"")
])

fix_file("vireon/core/engine.py", [
    ("import traceback\n", ""),
    ("import os\n", ""),
    ("import uuid\n", ""),
    ("f\"Digital Twin Event:\"", "\"Digital Twin Event:\"")
])

fix_file("vireon/core/fuzzer.py", [("import struct\n", "")])
fix_file("vireon/core/lsl_streamer.py", [("f\"[LSL Streamer] \"", "\"[LSL Streamer] \"")])
fix_file("vireon/core/ml_decoder.py", [("import time\n", "")])

fix_file("vireon/core/physics.py", [
    ("import math\n", ""),
    ("not tissue_type in", "tissue_type not in")
])

fix_file("vireon/core/privacy_leakage.py", [
    ("if len(data) == 0: return 0.0", "if len(data) == 0:\n            return 0.0")
])

fix_file("vireon/core/protocol.py", [
    ("import struct\n", ""),
    ("import json\n", ""),
    ("payload_type = struct.unpack('<H', header[2:4])[0]\n", "")
])

fix_file("vireon/core/redteam.py", [("import json\n", "")])

fix_file("vireon/core/sbom.py", [
    ("import json\n", ""),
    ("import hashlib\n", "")
])

fix_file("vireon/core/spdf_auditor.py", [("import json\n", "")])
fix_file("vireon/core/stride.py", [("import json\n", "")])

fix_file("vireon/core/twin.py", [
    ("import time\n", ""),
    ("import threading\n", ""),
    ("state = self.get_state()", "_state = self.get_state()"),
    ("firmware_state = self.device_stub.get_status() if self.device_stub else {}", "_firmware_state = self.device_stub.get_status() if self.device_stub else {}")
])

fix_file("vireon/core/validation.py", [
    ("import time\n", ""),
    ("import json\n", ""),
    ("f\"Validation Results:\"", "\"Validation Results:\""),
    ("if not self.metrics: return 0.0", "if not self.metrics:\n            return 0.0"),
    ("threshold = 5.0\n", ""),
    ("passed = len([m for m in self.metrics if m['rms_error'] < threshold])\n", "")
])

fix_file("vireon/ctf/engine.py", [("import json\n", "")])

fix_file("vireon/mcp_server.py", [
    ("import traceback\n", ""),
    ("from datetime import datetime\n", "")
])

fix_file("vireon/plugins/ble/attacks.py", [("import struct\n", "")])

fix_file("vireon/plugins/ble/emulator.py", [
    ("import struct\n", ""),
    ("from typing import Dict, List, Optional, Callable", "from typing import Dict, Optional, Callable")
])

fix_file("vireon/plugins/clinical/closed_loop.py", [("import numpy as np\n", "")])

fix_file("vireon/plugins/clinical/dbs_emulator.py", [
    ("import struct\n", ""),
    ("import json\n", ""),
    ("amplitude = params.get('amplitude', 3.0)\n", "")
])

fix_file("vireon/plugins/clinical/standards_mapping.py", [
    ("if condition: return \"Passed\"", "if condition:\n            return \"Passed\""),
    ("if isinstance(req, str): return [req]", "if isinstance(req, str):\n            return [req]")
])

fix_file("vireon/plugins/clinical/standards_registry.py", [("import json\n", "")])

fix_file("vireon/plugins/datasets/eeg_sample_reader.py", [("import sys\n", "")])

fix_file("vireon/plugins/datasets/fif_reader.py", [
    ("import warnings\n", ""),
    ("f\"Loaded FIF file:\"", "\"Loaded FIF file:\"")
])

fix_file("vireon/plugins/datasets/mne_reader.py", [
    ("import mne\n", ""),
    ("f\"MNE file loaded:\"", "\"MNE file loaded:\"")
])

fix_file("vireon/plugins/devices/emotiv_emulator.py", [("packet_counter = 0\n", "")])
fix_file("vireon/plugins/devices/hardware_bridge.py", [("import traceback\n", "")])
fix_file("vireon/plugins/devices/muse_emulator.py", [("import asyncio\n", "")])
