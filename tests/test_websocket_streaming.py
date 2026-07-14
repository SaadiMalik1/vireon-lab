import unittest
import json
import time
import asyncio
import threading
import os
from vireon.plugins.reports.ws_server import NeuroWebSocketServer

# Prevent proxy environment variables from intercepting loopback connections
for key in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
    os.environ.pop(key, None)

class TestWebSocketStreaming(unittest.TestCase):
    def test_websocket_broadcast(self):
        # Initialize WebSocket server on unique port
        server = NeuroWebSocketServer(host="127.0.0.1", port=9876)
        server.start()
        
        # Allow thread to bind
        time.sleep(0.15)
        
        received_messages = []
        client_loop = asyncio.new_event_loop()
        
        async def mock_client():
            import websockets
            try:
                # Connect to test port
                async with websockets.connect("ws://127.0.0.1:9876") as websocket:
                    # Wait for message broadcast
                    msg = await websocket.recv()
                    received_messages.append(msg)
            except Exception as e:
                received_messages.append(str(e))
                
        def run_client():
            asyncio.set_event_loop(client_loop)
            client_loop.run_until_complete(mock_client())
            client_loop.close()
            
        # Launch client thread
        client_thread = threading.Thread(target=run_client)
        client_thread.start()
        
        # Allow client to connect
        time.sleep(0.15)
        
        # Perform thread-safe broadcast from main thread
        test_payload = {"status": "nominal", "battery_level": 98.5}
        server.broadcast_sync(json.dumps(test_payload))
        
        # Wait for client thread to exit cleanly
        client_thread.join(timeout=2.0)
        
        # Tear down server
        server.stop()
        
        # Verify receipt and contents
        self.assertEqual(len(received_messages), 1)
        data = json.loads(received_messages[0])
        self.assertEqual(data["status"], "nominal")
        self.assertEqual(data["battery_level"], 98.5)

if __name__ == "__main__":
    unittest.main()
