import os
import pty
import fcntl
import termios
import tty
import threading
import time
from typing import List, Optional
import numpy as np
import logging

from vireon.sdk.state import IStateStore as StateStore

logger = logging.getLogger(__name__)

class OpenBCICytonEmulator:
    def __init__(self, twin: DigitalTwin):
        self.twin = twin
        
        self.master_fd = None
        self.slave_fd = None
        self.slave_name = ""
        
        self.running = False
        self.streaming = False
        self.sample_counter = 0
        
        self.read_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

    def start(self):
        with self.lock:
            if self.running:
                return
            
            # 1. Open PTY
            self.master_fd, self.slave_fd = pty.openpty()
            self.slave_name = os.ttyname(self.slave_fd)
            
            # Set PTY to raw mode to disable echoing, canonical buffering, newline mapping, etc.
            try:
                # Raw mode on master and slave
                tty.setraw(self.master_fd)
                tty.setraw(self.slave_fd)
                
                # Make sure block/read attributes are clean
                attrs = termios.tcgetattr(self.slave_fd)
                # Ensure no echo, no canonical processing, no output post-processing
                attrs[3] &= ~(termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG)
                attrs[1] &= ~termios.OPOST
                termios.tcsetattr(self.slave_fd, termios.TCSANOW, attrs)
            except Exception:
                logger.error("Warning setting raw tty attributes", exc_info=True)
            
            # Set non-blocking mode on master
            fl = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.master_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            
            self.running = True
            self.streaming = False
            self.sample_counter = 0
            
            # Start reader thread to handle commands
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            
            print(f"[OpenBCIEmulator] Virtual Cyton Serial Port opened: {self.slave_name}")
            print(f"[OpenBCIEmulator] Connect your GUI/BrainFlow client to: {self.slave_name}")

    def stop(self):
        with self.lock:
            if not self.running:
                return
            self.running = False
            self.streaming = False
            
        if self.read_thread:
            self.read_thread.join(timeout=1.0)
            self.read_thread = None
            
        with self.lock:
            if self.master_fd is not None:
                try:
                    os.close(self.master_fd)
                except Exception:
                    logger.debug("Failed to close master_fd during stop", exc_info=True)
                self.master_fd = None
                
            if self.slave_fd is not None:
                try:
                    os.close(self.slave_fd)
                except Exception:
                    logger.debug("Failed to close slave_fd during stop", exc_info=True)
                self.slave_fd = None
                
            print("[OpenBCIEmulator] Virtual Cyton Serial Port closed.")

    def _read_loop(self):
        buffer = b""
        while self.running:
            try:
                # Read from master_fd
                r = os.read(self.master_fd, 1024)
                if r:
                    buffer += r
                    # Process commands in buffer
                    buffer = self._process_commands(buffer)
            except BlockingIOError:
                # No data available, sleep briefly
                time.sleep(0.01)
            except Exception:
                # Handle disconnect or close
                if self.running:
                    logger.error("PTY read exception", exc_info=True)
                break

    def _process_commands(self, buffer: bytes) -> bytes:
        i = 0
        while i < len(buffer):
            cmd = chr(buffer[i])
            
            if cmd == 'v':
                # Reset and return board info
                print("[OpenBCIEmulator] Received Reset/Info command ('v')")
                response = b"OpenBCI V3 8-channel\nOn Board Ads1299\n$$$"
                self._write_to_client(response)
                i += 1
                
            elif cmd == 'b':
                # Start streaming
                print("[OpenBCIEmulator] Received Start Streaming command ('b')")
                with self.lock:
                    self.streaming = True
                i += 1
                
            elif cmd == 's':
                # Stop streaming
                print("[OpenBCIEmulator] Received Stop Streaming command ('s')")
                with self.lock:
                    self.streaming = False
                i += 1
                
            elif cmd == 'x':
                # Channel setting start. Find matching 'X'
                end_idx = buffer.find(b'X', i)
                if end_idx != -1:
                    config_cmd = buffer[i:end_idx+1]
                    print(f"[OpenBCIEmulator] Received channel configuration command: {config_cmd!r}")
                    # Respond with standard ack $$$
                    self._write_to_client(b"$$$")
                    i = end_idx + 1
                else:
                    # 'X' not found yet, keep in buffer and wait for more data
                    if len(buffer) - i > 256:
                        print("[OpenBCIEmulator] Buffer overflow waiting for 'X', dropping")
                        i += 1
                        continue
                    break
            else:
                # Unknown/unhandled single byte command, consume it
                if cmd in ['D', '?']:
                    print(f"[OpenBCIEmulator] Received query: {cmd}")
                    self._write_to_client(b"$$$")
                i += 1
                
        return buffer[i:]

    def _write_to_client(self, data: bytes):
        if self.master_fd is not None:
            try:
                os.write(self.master_fd, data)
            except Exception:
                logger.error("Error writing to master", exc_info=True)

    def send_eeg_data(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int):
        """
        Receives real-time data chunks from the ReplayEngine, serializes them
        into 33-byte Cyton binary packets, and streams them to the client.
        """
        
        with self.lock:
            if not self.streaming:
                return

        # Data shape is (channels, samples).
        num_samples = data.shape[1]
        
        # Cyton expects exactly 8 channels.
        channels_to_use = eeg_channels[:8]
        
        packet_bytes = bytearray()
        
        # Check if DigitalTwin has an active RF jam or packet drop rate configured
        # Fallback to 0.0 if not configured to maintain backwards compatibility
        drop_rate = getattr(self.twin, "rf_packet_drop_rate", 0.0)
        
        for s in range(num_samples):
            # Simulate RF dropped packets (Jamming or MTU overflow)
            if drop_rate > 0.0 and np.random.random() < drop_rate:
                # Skip constructing and sending this packet entirely
                self.sample_counter = (self.sample_counter + 1) % 256
                continue
                
            # 1. Start byte
            packet_bytes.append(0xA0)
            
            # 2. Sample counter
            packet_bytes.append(self.sample_counter & 0xFF)
            self.sample_counter = (self.sample_counter + 1) % 256
            
            # 3. 8 Channels of EEG (each 24-bit, 3 bytes)
            # Cyton scale factor is 4.5 / 24 / 8388607 = 2.2351742e-8 Volts = 0.02235174 uV
            scale = 0.02235174
            for c_idx in range(8):
                if c_idx < len(channels_to_use):
                    ch = channels_to_use[c_idx]
                    val_uv = data[ch, s]
                else:
                    val_uv = 0.0
                
                # Convert to integer count
                count = int(val_uv / scale)
                # Clip to 24-bit signed integer range
                count = max(-8388608, min(8388607, count))
                if count < 0:
                    count = (1 << 24) + count
                    
                packet_bytes.append((count >> 16) & 0xFF)
                packet_bytes.append((count >> 8) & 0xFF)
                packet_bytes.append(count & 0xFF)
                
            # 4. Accelerometer X, Y, Z (each 16-bit, 2 bytes)
            accel_x = 0
            accel_y = 0
            accel_z = 16384
            
            for accel_val in [accel_x, accel_y, accel_z]:
                val = int(accel_val) & 0xFFFF
                packet_bytes.append((val >> 8) & 0xFF)
                packet_bytes.append(val & 0xFF)
                
            # 5. Stop byte (0xC0 indicates standard packet)
            packet_bytes.append(0xC0)
            
        self._write_to_client(bytes(packet_bytes))
