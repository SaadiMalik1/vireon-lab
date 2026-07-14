import socket
import threading
import numpy as np
from typing import Any

class HardwareBridge:
    """
    Hardware-in-the-loop (HIL) TCP Loopback Server Bridge.
    Listens on local TCP port 9090 for protocol-equivalent binary telemetry
    from external board simulators, translating raw frames in real time.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 9090, num_channels: int = 8):
        self.host = host
        self.port = port
        self.num_channels = num_channels
        self.server_socket = None
        self.client_socket = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        
        # Internal queue to buffer parsed microvolt samples
        self.sample_buffer: list[Any] = []

    def start(self):
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        # Set timeout to prevent server thread from hanging indefinitely on accept
        self.server_socket.settimeout(0.5)
        
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print(f"[HardwareBridge] Loopback socket server listening on {self.host}:{self.port}...")

    def stop(self):
        self.running = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception:
                pass
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        if self.thread:
            self.thread.join(timeout=1.0)
        print("[HardwareBridge] Loopback socket server stopped.")

    def _listen_loop(self):
        raw_buffer = bytearray()
        
        while self.running:
            try:
                self.client_socket, addr = self.server_socket.accept()
                print(f"[HardwareBridge] Connection established with external board simulator: {addr}")
                self.client_socket.settimeout(0.2)
            except socket.timeout:
                continue
            except Exception:
                break

            while self.running:
                try:
                    data = self.client_socket.recv(1024)
                    if not data:
                        print("[HardwareBridge] Client disconnected.")
                        break
                    raw_buffer.extend(data)
                    
                    # Parse standard 33-byte Cyton protocol packets
                    while len(raw_buffer) >= 33:
                        # Find sync header
                        sync_idx = raw_buffer.find(b'\xA0')
                        if sync_idx == -1:
                            # No header found, discard entire buffer except last byte (could be partial header)
                            del raw_buffer[:-1]
                            break
                        elif sync_idx > 0:
                            # Discard garbage before header
                            del raw_buffer[:sync_idx]
                            if len(raw_buffer) < 33:
                                break
                                
                        # Verify packet footer
                        if raw_buffer[32] != 0xC0:
                            # Mismatched footer, discard this header and try again
                            del raw_buffer[:1]
                            continue
                            
                        # Extract valid packet
                        packet = raw_buffer[:33]
                        del raw_buffer[:33]
                        
                        # Unpack 8 EEG channels * 3 bytes (24-bit big-endian signed integers)
                        channel_data = []
                        for c in range(self.num_channels):
                            offset = 2 + c * 3
                            b0 = packet[offset]
                            b1 = packet[offset + 1]
                            b2 = packet[offset + 2]
                            
                            # Shift and reconstruct 24-bit signed int
                            val = (b0 << 16) | (b1 << 8) | b2
                            if val & 0x800000:
                                val -= 0x1000000 # Unpack two's complement sign
                                
                            # Convert to microvolts using standard Cyton scale factor:
                            # scale_fac = 4.5 / (2^23 - 1) / gain * 1e6
                            # With default gain=24: 0.02235 microvolts/count
                            volts = val * 0.02235174
                            channel_data.append(volts)
                            
                        with self.lock:
                            self.sample_buffer.append(channel_data)
                            # Clamp buffer size to avoid memory overflow if BCI is lagging
                            if len(self.sample_buffer) > 2000:
                                self.sample_buffer = self.sample_buffer[-2000:]
                                
                except socket.timeout:
                    continue
                except Exception:
                    print("[HardwareBridge] Read error or link dropped.")
                    break

    def read_chunk(self, start_sample: int, num_samples: int = None) -> np.ndarray:
        """
        Pops samples from parsed sample buffer.
        Compatible with both single-argument (num_samples) and double-argument (start, count) signatures.
        """
        n = start_sample if num_samples is None else num_samples
        
        samples_to_return = []
        with self.lock:
            take = min(n, len(self.sample_buffer))
            if take > 0:
                samples_to_return = self.sample_buffer[:take]
                del self.sample_buffer[:take]

        # Generate output array of shape (num_channels, n)
        out = np.zeros((self.num_channels, n))
        
        # Populate with available received loopback samples
        for i, s in enumerate(samples_to_return):
            out[:, i] = s
            
        # Fill remainder with NaN if buffer starved, enforcing strict data provenance
        starve_count = n - len(samples_to_return)
        if starve_count > 0:
            offset = len(samples_to_return)
            out[:, offset:] = np.full((self.num_channels, starve_count), np.nan)
            
        return out
