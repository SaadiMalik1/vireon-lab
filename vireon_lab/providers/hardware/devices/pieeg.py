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

import time
import threading
from vireon_lab.providers.hardware.devices import IDeviceWrapper
import numpy as np
from typing import List, Dict, Any, Optional

# Dynamic mock of Raspberry Pi GPIO and spidev if not present
try:
    import RPi.GPIO as GPIO
    import spidev
    HAS_HARDWARE_LIBS = True
except ImportError:
    HAS_HARDWARE_LIBS = False

    # Mock RPi.GPIO for non-Pi architectures
    class GPIO_Mock:
        BCM = 11
        OUT = 1
        IN = 2
        FALLING = 3
        
        def __init__(self):
            self.pins: Dict[int, int] = {}
            self.callbacks: Dict[int, Any] = {}

        def setmode(self, mode):
            pass

        def setup(self, pin: int, direction: int):
            self.pins[pin] = direction

        def output(self, pin: int, value: int):
            pass

        def add_event_detect(self, pin: int, edge: int, callback: Any):
            self.callbacks[pin] = callback

        def cleanup(self):
            self.pins.clear()
            self.callbacks.clear()

    GPIO = GPIO_Mock()

    # Mock spidev for non-Pi architectures
    class MockSpiDev:
        def __init__(self):
            self.bus = 0
            self.device = 0
            self.max_speed_hz = 4000000
            self.mode = 1
            # Reference signal count generator for mock
            self.tick = 0

        def open(self, bus: int, device: int):
            self.bus = bus
            self.device = device

        def close(self):
            pass

        def xfer2(self, tx_list: List[int]) -> List[int]:
            # Emulates the ADS1299 response frame (27 bytes: 3 status + 24 EEG data)
            rx = [0] * 27
            
            # Status: 0xC00000
            rx[0] = 0xC0
            rx[1] = 0x00
            rx[2] = 0x00
            
            # Generate synthetic sine wave data on channels 1-8
            # Emulating standard 250Hz frequency
            t = self.tick / 250.0
            self.tick += 1
            
            scale = 0.02235174
            for ch in range(8):
                # Custom sine wave for each channel
                val_uv = 30.0 * np.sin(2 * np.pi * 10.0 * t + ch) + np.random.normal(0, 1.5)
                
                # Convert to counts
                count = int(val_uv / scale)
                count = max(-8388608, min(8388607, count))
                if count < 0:
                    count = (1 << 24) + count
                    
                rx[3 + ch*3] = (count >> 16) & 0xFF
                rx[4 + ch*3] = (count >> 8) & 0xFF
                rx[5 + ch*3] = count & 0xFF
                
            return rx

        def writebytes(self, tx_list: List[int]):
            pass

class ADS1299SPIEmulator:
    """
    Simulates the ADS1299 registers and byte framing over SPI.
    """
    def __init__(self):
        if HAS_HARDWARE_LIBS:
            self.spi = spidev.SpiDev()
        else:
            self.spi = MockSpiDev()

    def open(self, bus: int = 0, device: int = 0):
        self.spi.open(bus, device)
        self.spi.max_speed_hz = 4000000
        self.spi.mode = 1

    def close(self):
        self.spi.close()

    def read_frame(self) -> List[int]:
        # Send 27 dummy bytes to clock out the status + 8 EEG channels (24-bit each)
        return self.spi.xfer2([0] * 27)

class PiEEGSpiBoard:
    """
    Custom BoardShim-compatible interface reading directly from PiEEG SPI bus.
    Allows running hardware-level SPI readers within VIREON's architecture.
    """
    def __init__(self, spi_bus: int = 0, spi_device: int = 0):
        self.spi_bus = spi_bus
        self.spi_device = spi_device
        self.ads = ADS1299SPIEmulator()
        
        self._prepared = False
        self._streaming = False
        self.read_thread: Optional[threading.Thread] = None
        
        # Buffer for EEG data (32 channels total to match Brainflow output shape)
        self.buffer_lock = threading.Lock()
        self.buffer: List[np.ndarray] = []
        
        # Hardware Pins (PiEEG mappings)
        self.drdy_pin = 22 # DRDY pin
        self.reset_pin = 27 # RESET/PWDN

    def prepare_session(self):
        if self._prepared:
            return
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.drdy_pin, GPIO.IN)
        GPIO.setup(self.reset_pin, GPIO.OUT)
        
        # Reset ADS1299
        GPIO.output(self.reset_pin, 1)
        time.sleep(0.01)
        GPIO.output(self.reset_pin, 0)
        time.sleep(0.01)
        GPIO.output(self.reset_pin, 1)
        time.sleep(0.01)
        
        # Open SPI
        self.ads.open(self.spi_bus, self.spi_device)
        self._prepared = True

    def is_prepared(self) -> bool:
        return self._prepared

    def start_stream(self, num_samples: int = 1200):
        if not self._prepared:
            raise Exception("Session not prepared. Call prepare_session first.")
        
        if self._streaming:
            return
            
        self._streaming = True
        self.read_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.read_thread.start()

    def stop_stream(self):
        if not self._streaming:
            return
        self._streaming = False
        if self.read_thread:
            self.read_thread.join(timeout=1.0)
            self.read_thread = None

    def release_session(self):
        self.stop_stream()
        self.ads.close()
        try:
            GPIO.cleanup()
        except Exception:
            pass
        self._prepared = False

    def _stream_loop(self):
        # Scale factor: 4.5V VREF, Gain 24, 24-bit
        scale = 0.02235174
        
        last_tick = time.time()
        while self._streaming:
            if HAS_HARDWARE_LIBS:
                # On real Pi, wait for DRDY falling edge (Hardware interrupt)
                # DRDY goes low when new data is ready (250 times per second)
                # Here we poll DRDY pin state with a micro-sleep
                while GPIO.input(self.drdy_pin) == 1 and self._streaming:
                    time.sleep(0.0005)
            else:
                # Simulated 250Hz clock sleep (4 ms)
                now = time.time()
                elapsed = now - last_tick
                sleep_time = 0.004 - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                last_tick = time.time()
                
            if not self._streaming:
                break
                
            try:
                # Read 27-byte ADS1299 frame
                frame = self.ads.read_frame()
                
                # Check frame signature (0xC0 status prefix)
                if frame[0] != 0xC0:
                    continue
                    
                # Parse 8 channels of 24-bit data
                sample_data = np.zeros(32)
                
                # Package counter (placeholder at index 0)
                sample_data[0] = len(self.buffer)
                
                for ch in range(8):
                    offset = 3 + ch * 3
                    b1 = frame[offset]
                    b2 = frame[offset+1]
                    b3 = frame[offset+2]
                    
                    # Reconstruction from 24-bit two's complement
                    count = (b1 << 16) | (b2 << 8) | b3
                    if count & 0x800000:
                        count -= 0x1000000
                    
                    # Convert to microvolts
                    sample_data[1 + ch] = count * scale
                    
                # Store sample
                with self.buffer_lock:
                    self.buffer.append(sample_data)
            except Exception as e:
                print(f"[PiEEG] SPI read error: {e}")
                time.sleep(0.01)

    def get_board_data(self) -> np.ndarray:
        with self.buffer_lock:
            if not self.buffer:
                return np.empty((32, 0))
            
            # Convert list of 1D arrays into a 2D array of shape (32, num_samples)
            data = np.column_stack(self.buffer)
            self.buffer.clear()
            return data

class PiEEGBoardWrapper(IDeviceWrapper):
    """
    PiEEG Device Wrapper.
    Exposes either physical PiEEG SPI board or high-fidelity simulated SPI board.
    """
    def __init__(self, spi_bus: int = 0, spi_device: int = 0, **kwargs):
        self.board = PiEEGSpiBoard(spi_bus, spi_device)

    def get_board(self) -> PiEEGSpiBoard:
        return self.board

    def get_eeg_channels(self) -> List[int]:
        # Channels 1-8 represent the 8 EEG channels
        return [1, 2, 3, 4, 5, 6, 7, 8]

    def start(self):
        self.board.prepare_session()
        self.board.start_stream()

    def stop(self):
        self.board.stop_stream()
        self.board.release_session()

    def read_chunk(self, start_sample: int = 0, num_samples: int = -1) -> np.ndarray:
        data = self.board.get_board_data()
        channels = self.get_eeg_channels()
        if data.shape[1] > 0:
            return data[channels, :]
        return np.empty((len(channels), 0))

    def send_eeg_data(self, data: Any) -> None:
        pass
