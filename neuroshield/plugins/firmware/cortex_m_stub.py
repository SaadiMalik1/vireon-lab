"""
ARM Cortex-M Firmware Emulation Stub.

Provides a simplified memory map and register file to simulate the behavior of
a micro-controller running NeuroShield firmware. Includes basic checks for
memory corruption and buffer overflows during OTA updates or command handling.
"""

from typing import Dict, Tuple, Optional
import struct

class CortexMStub:
    def __init__(self):
        # Simplified Memory Map
        self.FLASH_BASE = 0x08000000
        self.FLASH_SIZE = 512 * 1024 # 512 KB
        
        self.SRAM_BASE = 0x20000000
        self.SRAM_SIZE = 128 * 1024 # 128 KB
        
        self.PERIPH_BASE = 0x40000000
        
        # Segregation Zones (MPU Emulation - IEC 62304)
        self.CLASS_A_BASE = 0x20000000
        self.CLASS_A_SIZE = 64 * 1024 # 64 KB Telemetry
        
        self.CLASS_C_BASE = 0x20010000
        self.CLASS_C_SIZE = 64 * 1024 # 64 KB Stimulation Control
        
        self.current_execution_class = "CLASS_A"
        
        # Memory storage
        self.sram = bytearray(self.SRAM_SIZE)
        self.flash = bytearray(self.FLASH_SIZE)
        
        # Registers: R0-R12, SP (R13), LR (R14), PC (R15), xPSR
        self.registers = {f"R{i}": 0 for i in range(13)}
        self.registers["SP"] = self.SRAM_BASE + self.SRAM_SIZE
        self.registers["LR"] = 0xFFFFFFFF
        self.registers["PC"] = self.FLASH_BASE
        self.registers["xPSR"] = 0x01000000
        
        # Security Monitor state
        self.crashed = False
        self.crash_reason = ""
        self.overflow_detected = False

    def reset(self):
        self.registers["SP"] = self.SRAM_BASE + self.SRAM_SIZE
        self.registers["PC"] = self.FLASH_BASE
        self.crashed = False
        self.crash_reason = ""
        self.overflow_detected = False

    def write_memory(self, address: int, data: bytes) -> bool:
        """Writes data to memory. Returns True if successful, False if fault."""
        if self.crashed:
            return False
            
        # Check SRAM write
        if self.SRAM_BASE <= address < self.SRAM_BASE + self.SRAM_SIZE:
            offset = address - self.SRAM_BASE
            if offset + len(data) > self.SRAM_SIZE:
                self._trigger_fault("Memory Access Violation: SRAM Buffer Overflow")
                return False
            
            # Simulated stack canary check (very basic)
            # If writing over the stack pointer region and it contains our canary
            if offset <= (self.registers["SP"] - self.SRAM_BASE) < offset + len(data):
                self._trigger_fault("Stack Smashing Detected")
                return False
                
            # IEC 62304 Segregation Enforcement
            if self.current_execution_class == "CLASS_A" and self.CLASS_C_BASE <= address < self.CLASS_C_BASE + self.CLASS_C_SIZE:
                self._trigger_fault("MPU Fault: IEC 62304 Segregation Violation (Class A wrote to Class C)")
                return False
                
            self.sram[offset:offset+len(data)] = data
            return True
            
        # Check Flash write (simulated OTA update)
        elif self.FLASH_BASE <= address < self.FLASH_BASE + self.FLASH_SIZE:
            offset = address - self.FLASH_BASE
            if offset + len(data) > self.FLASH_SIZE:
                self._trigger_fault("Memory Access Violation: Flash Overflow")
                return False
            self.flash[offset:offset+len(data)] = data
            return True
            
        else:
            self._trigger_fault(f"HardFault: Invalid Memory Access at 0x{address:08X}")
            return False

    def _trigger_fault(self, reason: str):
        self.crashed = True
        self.crash_reason = reason
        if "Overflow" in reason or "Smashing" in reason:
            self.overflow_detected = True
        print(f"[FirmwareEmulator] {reason} (PC=0x{self.registers['PC']:08X})")

class FirmwareSecurityMonitor:
    def __init__(self, emulator: CortexMStub):
        self.emulator = emulator
        
    def check_health(self) -> Tuple[bool, str]:
        if self.emulator.crashed:
            return False, self.emulator.crash_reason
        return True, "Nominal"
