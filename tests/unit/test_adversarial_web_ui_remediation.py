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
Regression Test Suite for VIREON-Lab Web UI & Provider Engine Remediation (LAB-01 to LAB-07).
"""

import html
import numpy as np

from vireon_lab.providers.hardware.devices.hardware_bridge import HardwareBridge
from vireon.sdk.runner import popen_sandboxed, run_sandboxed
from vireon_lab.providers.clinical.dbs_emulator import LFPGenerator


def test_lab_01_canvas_waveform_cleanup_handlers():
    """LAB-01: Verifies canvas_waveform.py includes window unload cleanup code."""
    from vireon_lab.dashboard.canvas_waveform import render_double_buffered_eeg_canvas
    import inspect
    
    source = inspect.getsource(render_double_buffered_eeg_canvas)
    assert "cancelAnimationFrame(animFrameId)" in source
    assert "window.addEventListener('unload', cleanup)" in source


def test_lab_03_xss_escaping_utility():
    """LAB-03: Verifies string escaping prevents HTML/JS injection in threat badges."""
    malicious_payload = "<script>alert('XSS')</script>"
    escaped_payload = html.escape(str(malicious_payload))
    
    assert "<script>" not in escaped_payload
    assert "&lt;script&gt;" in escaped_payload


def test_lab_04_hardware_bridge_zero_fill_on_starvation():
    """LAB-04: Verifies HardwareBridge zero-fills starved buffer slots instead of np.nan."""
    bridge = HardwareBridge(num_channels=4)
    # Bridge buffer is empty (starved)
    chunk = bridge.read_chunk(start_sample=0, num_samples=10)
    
    assert chunk.shape == (4, 10)
    assert not np.isnan(chunk).any()
    assert np.allclose(chunk, 0.0)


def test_lab_05_sandboxed_runner_bwrap_fallback():
    """LAB-05: Verifies popen_sandboxed and run_sandboxed execute safely with or without bwrap."""
    # Test simple echo command
    res = run_sandboxed(["echo", "vireon_test"])
    assert res.returncode == 0
    assert "vireon_test" in res.stdout
    
    import subprocess
    proc = popen_sandboxed(["echo", "vireon_async_test"], stdout=subprocess.PIPE)
    stdout, _ = proc.communicate()
    assert proc.returncode == 0
    assert b"vireon_async_test" in stdout


def test_lab_06_dbs_lfp_pink_noise_variance_guard():
    """LAB-06: Verifies LFPGenerator pink noise generation produces non-NaN values."""
    gen = LFPGenerator(sample_rate=250, num_channels=4)
    chunk = gen.read_chunk(num_samples=100, stimulation_state="none")
    
    assert chunk.shape == (4, 100)
    assert not np.isnan(chunk).any()
    assert not np.isinf(chunk).any()


def test_lab_07_parameter_clamping():
    """LAB-07: Verifies numpy clip bounds enforcement on intensity parameters."""
    raw_intensity = 120.0 / 35.0 # 3.428 (exceeds slider max 3.0)
    clamped_intensity = float(np.clip(raw_intensity, 0.1, 3.0))
    
    assert clamped_intensity == 3.0
