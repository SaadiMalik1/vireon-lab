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

import pytest
from unittest.mock import patch, MagicMock
from vireon_lab.providers.firmware.qemu_hil import QemuCortexMEmulator

@patch("os.path.exists", return_value=True)
@patch("subprocess.Popen")
@patch("time.sleep", return_value=None)
def test_qemu_hil_start_stop(mock_sleep, mock_popen, mock_exists):
    mock_process = MagicMock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process
    
    emulator = QemuCortexMEmulator("dummy.bin")
    emulator.start(wait_for_gdb=False)
    
    assert emulator.running is True
    mock_popen.assert_called_once()
    
    # Check command line args
    cmd = mock_popen.call_args[0][0]
    assert "qemu-system-arm" in cmd
    assert "-M" in cmd
    assert "lm3s6965evb" in cmd
    assert "-kernel" in cmd
    assert "dummy.bin" in cmd
    assert "-s" in cmd
    
    emulator.stop()
    assert emulator.running is False
    mock_process.terminate.assert_called_once()

@patch("os.path.exists", return_value=True)
@patch("subprocess.Popen")
@patch("time.sleep", return_value=None)
def test_qemu_hil_crashed_on_start(mock_sleep, mock_popen, mock_exists):
    mock_process = MagicMock()
    # poll returns non-None indicating crash
    mock_process.poll.return_value = 1
    mock_process.communicate.return_value = (b"", b"qemu error")
    mock_popen.return_value = mock_process
    
    emulator = QemuCortexMEmulator("dummy.bin")
    
    with pytest.raises(RuntimeError, match="QEMU failed to start. err: qemu error"):
        emulator.start()
