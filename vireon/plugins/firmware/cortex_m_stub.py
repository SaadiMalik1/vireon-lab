"""
ARM Cortex-M Firmware Emulation Stub.

Provides a simplified memory map and register file to simulate the behavior of
a micro-controller running VIREON firmware. Includes basic checks for
memory corruption and buffer overflows during OTA updates or command handling.
"""

from typing import Tuple
import struct

class CortexMStub:
    def __init__(self):
        # Simplified Memory Map
        self.BOOTLOADER_BASE = 0x08000000
        self.BOOTLOADER_SIZE = 32 * 1024 # 32 KB
        self.APP_BASE = 0x08008000
        self.APP_SIZE = 480 * 1024 # 480 KB
        
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
        
        # Hardware Fuses (Immutable State)
        self.efuses = {
            "MIN_SVN": 1, # Minimum Security Version Number allowed to boot/flash
            "DEBUG_LOCKED": True
        }
        
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

    def recover(self):
        """Recover from a crashed state (simulated reboot)."""
        print("[FirmwareEmulator] Executing recovery/reboot sequence...")
        self.reset()

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

    def process_ota_update(self, payload: bytes) -> bool:
        """
        Simulates Secure Bootloader processing an OTA update payload.
        Expects a 36-byte header containing the SVN (4 bytes) and SHA256 Signature (32 bytes).
        Format: [SVN (4 bytes)] + [Signature (32 bytes)] + [Binary Payload...]
        """
        if self.crashed:
            return False
            
        if len(payload) < 36:
            self._trigger_fault("OTA Error: Payload too short to contain header and signature.")
            return False
            
        # Extract 4-byte SVN (little-endian unsigned int)
        payload_svn = struct.unpack('<I', payload[:4])[0]
        
        signature = payload[4:68]
        firmware_binary = payload[68:]
        
        # Verify real asymmetric signature (Ed25519) instead of SHA-256 hash (SEC-5)
        try:
            if not hasattr(self, "ota_public_key"):
                self._trigger_fault("Secure Boot Fault: No public key provisioned.")
                return False
            self.ota_public_key.verify(signature, firmware_binary)
        except Exception:
            self._trigger_fault("Secure Boot Fault: Firmware signature verification failed.")
            return False
        
        # Anti-Rollback Check against hardware eFuses
        if payload_svn < self.efuses["MIN_SVN"]:
            self._trigger_fault(f"Secure Boot Fault: Anti-Rollback violation. " 
                                f"Payload SVN ({payload_svn}) < MIN_SVN ({self.efuses['MIN_SVN']})")
            return False
            
        # Simulate writing the rest of the payload to Flash memory (APP region)
        success = self.write_memory(self.APP_BASE, firmware_binary)
        
        if success:
            print(f"[CortexMStub] OTA Update Successful. Flashed {len(firmware_binary)} bytes.")
            # Update the eFuse to prevent future rollbacks if the new SVN is higher
            if payload_svn > self.efuses["MIN_SVN"]:
                print(f"[CortexMStub] Updating eFuse MIN_SVN: {self.efuses['MIN_SVN']} -> {payload_svn}")
                self.efuses["MIN_SVN"] = payload_svn
            
        return success

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
