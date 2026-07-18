import subprocess
import time
import socket
import os
from typing import Optional, Tuple

class QemuCortexMEmulator:
    """
    Hardware-In-The-Loop (HIL) QEMU Emulator.
    Spawns a real qemu-system-arm process to execute cross-compiled firmware.
    Bridges QEMU's virtual UART to a local TCP socket for telemetry injection.
    """
    def __init__(self, firmware_path: str, machine: str = "lm3s6965evb", cpu: str = "cortex-m3"):
        self.firmware_path = firmware_path
        self.machine = machine
        self.cpu = cpu
        self.process: Optional[subprocess.Popen] = None
        self.uart_port = 9091
        self.gdb_port = 1234
        self.running = False
        
        if not os.path.exists(self.firmware_path):
            raise FileNotFoundError(f"Firmware binary not found: {self.firmware_path}")

    def start(self, wait_for_gdb: bool = False):
        """
        Launch QEMU process.
        -nographic: disable graphical output
        -serial tcp::9091,server,nowait: expose UART over TCP
        -s: shorthand for -gdb tcp::1234
        -S: freeze CPU at startup (wait for GDB)
        """
        cmd = [
            "qemu-system-arm",
            "-M", self.machine,
            "-cpu", self.cpu,
            "-kernel", self.firmware_path,
            "-nographic",
            "-serial", f"tcp::{self.uart_port},server,nowait",
        ]
        
        if wait_for_gdb:
            cmd.extend(["-s", "-S"])
        else:
            # We still enable GDB stub in background
            cmd.extend(["-s"])
            
        print(f"[QemuHIL] Launching QEMU (sandboxed): {' '.join(cmd)}")
        from vireon.sdk.runner import popen_sandboxed
        self.process = popen_sandboxed(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.running = True
        
        # Give QEMU a moment to bind sockets
        time.sleep(1.0)
        
        # Check if process crashed immediately
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            raise RuntimeError(f"QEMU failed to start. err: {stderr.decode()}")
            
    def stop(self):
        self.running = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            print("[QemuHIL] QEMU stopped.")

    def check_health(self) -> Tuple[bool, str]:
        if not self.process:
            return False, "Process not started"
        
        retcode = self.process.poll()
        if retcode is not None:
            return False, f"QEMU crashed or exited with code {retcode}"
            
        return True, "Nominal"

    def interact_uart(self) -> socket.socket:
        """
        Returns a connected socket to the QEMU UART port for telemetry streaming.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", self.uart_port))
        return s
