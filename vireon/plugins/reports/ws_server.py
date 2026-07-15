import asyncio
import threading
import urllib.parse
from typing import Set, Optional, Any
import websockets

class NeuroWebSocketServer:
    """
    Asynchronous WebSocket server for broadcasting real-time VIREON simulation telemetry.
    Runs its own asyncio loop inside a dedicated background thread.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 7778, token: str = ""):
        self.host = host
        self.port = port
        self.token = token
        self.clients: Set[Any] = set()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.server = None
        self.thread: Optional[threading.Thread] = None

    async def handler(self, websocket: Any):
        """Handle incoming client connections."""
        
        # Authenticate connection using WS_TOKEN
        if hasattr(websocket, 'request'):
            path = getattr(websocket.request, 'path', '')
        else:
            path = getattr(websocket, 'path', '')
            
        query = urllib.parse.urlparse(path).query
        params = urllib.parse.parse_qs(query)
        
        if self.token and params.get("token", [""])[0] != self.token:
            await websocket.close(1008, "Unauthorized")
            return

        self.clients.add(websocket)
        try:
            # Keep connection open and listen for close events
            async for _ in websocket:
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if websocket in self.clients:
                self.clients.remove(websocket)

    async def _broadcast(self, message: str):
        """Send message to all active clients concurrently."""
        if not self.clients:
            return
        # Broadcast to all clients and swallow individual connection failures
        await asyncio.gather(
            *[client.send(message) for client in self.clients],
            return_exceptions=True
        )

    def broadcast_sync(self, message: str):
        """Thread-safe synchronous broadcast entrypoint called from ReplayEngine thread."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast(message), self.loop)

    def _run(self):
        """Initialize event loop and start server."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        async def main_task():
            # Bind and start serving
            self.server = await websockets.serve(self.handler, self.host, self.port)
            # Sleep indefinitely until server is closed
            await self.server.wait_closed()
            
        try:
            self.loop.run_until_complete(main_task())
        except Exception:
            pass
        finally:
            # Graceful cancellation of any pending tasks (e.g. server close task)
            try:
                pending = asyncio.all_tasks(self.loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            self.loop.close()

    def start(self):
        """Spawn the background thread running the event loop."""
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop server and signal thread exit."""
        if self.server:
            self.server.close()
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
