import json
import subprocess
import threading
from typing import Optional

from vireon.sdk.interfaces import IProvider, OrchestratorContext
from vireon.sdk.manifest import CapabilityManifest
from vireon.core.event_bus import Event

class SubprocessProvider(IProvider):
    """
    Level 1 Isolation Provider (Subprocess IPC).
    Executes an untrusted plugin in a separate child process.
    Communication is facilitated via JSON over stdin/stdout.
    The host enforces capabilities via the CapabilityEngine proxies.
    """
    def __init__(self, command: list[str], manifest: CapabilityManifest):
        self.command = command
        self._manifest = manifest
        self.process: Optional[subprocess.Popen] = None
        self.context: Optional[OrchestratorContext] = None
        self._running = False

    @property
    def manifest(self) -> CapabilityManifest:
        return self._manifest

    def initialize(self, context: OrchestratorContext) -> None:
        self.context = context
        print(f"[SubprocessProvider] Spawning isolated plugin: {' '.join(self.command)}")
        
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self._running = True

        # Start a listener thread for incoming IPC events
        self.listener_thread = threading.Thread(target=self._ipc_listener, daemon=True)
        self.listener_thread.start()

        # Send initialization data to the subprocess
        self._send_ipc({
            "type": "initialize",
            "manifest": {
                "name": self.manifest.name,
                "version": self.manifest.version
            }
        })

    def on_tick(self, sim_clock: float, dt: float) -> None:
        # Send tick event to subprocess
        self._send_ipc({
            "type": "tick",
            "sim_clock": sim_clock,
            "dt": dt
        })

    def shutdown(self) -> None:
        self._running = False
        if self.process:
            self._send_ipc({"type": "shutdown"})
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                print(f"[SubprocessProvider] Force terminating {self.manifest.name}...")
                self.process.kill()

    def _send_ipc(self, payload: dict) -> None:
        if self.process and self.process.stdin and self._running:
            try:
                self.process.stdin.write(json.dumps(payload) + "\n")
                self.process.stdin.flush()
            except IOError as e:
                print(f"[SubprocessProvider] IPC Send Error to {self.manifest.name}: {e}")
                self._running = False

    def _ipc_listener(self) -> None:
        """Reads incoming JSON messages from the isolated plugin."""
        if not self.process or not self.process.stdout:
            return

        while self._running:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break

                payload = json.loads(line)
                msg_type = payload.get("type")

                if msg_type == "publish":
                    # Subprocess wants to publish an event
                    event = Event(
                        topic=payload.get("topic"),
                        data=payload.get("data", {}),
                        source=self.manifest.name
                    )
                    # This goes through the CapabilityEngine proxy
                    try:
                        self.context.event_bus.publish(event)
                    except Exception as e:
                        print(f"[SubprocessProvider] Security Violation by {self.manifest.name}: {e}")
                
                elif msg_type == "state_get":
                    # Subprocess wants to read state
                    key = payload.get("key")
                    try:
                        val = self.context.state_store.get(key)
                        self._send_ipc({
                            "type": "state_response",
                            "key": key,
                            "value": val
                        })
                    except Exception as e:
                        print(f"[SubprocessProvider] Security Violation by {self.manifest.name}: {e}")
                        
                elif msg_type == "state_set":
                    # Subprocess wants to mutate state
                    key = payload.get("key")
                    val = payload.get("value")
                    try:
                        self.context.state_store.set(key, val)
                    except Exception as e:
                        print(f"[SubprocessProvider] Security Violation by {self.manifest.name}: {e}")

            except json.JSONDecodeError:
                # Malformed IPC message
                continue
            except IOError:
                break
