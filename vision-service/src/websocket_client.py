"""
XADRAS Vision Service - WebSocket Client
Handles communication with the Django backend
"""

import asyncio
import json
import time
from typing import Optional, Callable, Any
from dataclasses import dataclass

from .config import config


@dataclass
class BoardUpdate:
    """Board update message to send to backend"""
    fen: str
    confidence: float
    markers_visible: int
    timestamp: float
    possible_move: Optional[str] = None


class WebSocketClient:
    """
    WebSocket client for backend communication.
    
    Sends board updates to the Django VisionConsumer.
    Handles reconnection on disconnect.
    """
    
    def __init__(self):
        self.ws_url = config.backend_ws_url
        self.camera_token = config.camera_token
        self.camera_id = config.camera_id
        
        self.websocket = None
        self.connected = False
        self.last_fen: Optional[str] = None
        self.message_queue: list = []
        
        # Callbacks
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_message: Optional[Callable[[dict], None]] = None
    
    async def connect(self) -> bool:
        """Connect to the WebSocket server"""
        try:
            import websockets
            
            # Build connection URL with authentication
            url = self.ws_url
            if self.camera_token:
                url = f"{url}?token={self.camera_token}"
            
            print(f"[WebSocket] Connecting to {self.ws_url}...")
            
            self.websocket = await websockets.connect(
                url,
                ping_interval=30,
                ping_timeout=10
            )
            
            self.connected = True
            print("[WebSocket] Connected successfully")
            
            # Send identification message
            await self._send_identification()
            
            if self.on_connected:
                self.on_connected()
            
            # Send any queued messages
            await self._flush_queue()
            
            return True
            
        except ImportError:
            print("[WebSocket] websockets library not installed. Install with: pip install websockets")
            return False
        except Exception as e:
            print(f"[WebSocket] Connection failed: {e}")
            self.connected = False
            return False
    
    async def _send_identification(self):
        """Send camera identification to backend"""
        message = {
            "type": "camera_identify",
            "camera_id": self.camera_id,
            "camera_token": self.camera_token,
            "timestamp": time.time()
        }
        await self._send(message)
    
    async def disconnect(self):
        """Disconnect from the WebSocket server"""
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        
        self.websocket = None
        self.connected = False
        print("[WebSocket] Disconnected")
        
        if self.on_disconnected:
            self.on_disconnected()
    
    async def send_board_update(self, update: BoardUpdate) -> bool:
        """
        Send board update to backend.
        Only sends if FEN has changed from last update.
        """
        # Skip if FEN hasn't changed
        if update.fen == self.last_fen:
            return True
        
        message = {
            "type": "board_update",
            "data": {
                "camera_id": self.camera_id,
                "fen": update.fen,
                "confidence": update.confidence,
                "markers_visible": update.markers_visible,
                "timestamp": update.timestamp,
                "move": update.possible_move
            }
        }
        
        success = await self._send(message)
        
        if success:
            self.last_fen = update.fen
            fen_display = update.fen[:30] if len(update.fen) > 30 else update.fen
            print(f"[WebSocket] Sent board update: {fen_display}...")
        
        return success
    
    async def _send(self, message: dict) -> bool:
        """Send a message to the WebSocket"""
        if not self.connected or self.websocket is None:
            # Queue message for later
            self.message_queue.append(message)
            return False
        
        try:
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            print(f"[WebSocket] Send error: {e}")
            self.connected = False
            self.message_queue.append(message)
            return False
    
    async def _flush_queue(self):
        """Send all queued messages"""
        while self.message_queue and self.connected:
            message = self.message_queue.pop(0)
            try:
                await self.websocket.send(json.dumps(message))
            except Exception as e:
                print(f"[WebSocket] Queue flush error: {e}")
                self.message_queue.insert(0, message)
                break
    
    async def receive_loop(self):
        """Listen for messages from the server"""
        if not self.websocket:
            return
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    print(f"[WebSocket] Invalid JSON received: {message}")
        except Exception as e:
            print(f"[WebSocket] Receive error: {e}")
            self.connected = False
    
    async def _handle_message(self, data: dict):
        """Handle incoming message from server"""
        msg_type = data.get("type")
        
        if msg_type == "connection_established":
            print("[WebSocket] Server acknowledged connection")
        
        elif msg_type == "board_update_ack":
            pass  # Acknowledgment received
        
        elif msg_type == "error":
            print(f"[WebSocket] Server error: {data.get('message')}")
        
        else:
            if self.on_message:
                self.on_message(data)
    
    async def run_with_reconnect(self, check_interval: float = 5.0):
        """
        Run the WebSocket client with automatic reconnection.
        
        This is meant to be run as a background task.
        """
        while True:
            if not self.connected:
                await self.connect()
            
            if self.connected:
                try:
                    await self.receive_loop()
                except Exception as e:
                    print(f"[WebSocket] Error in receive loop: {e}")
            
            self.connected = False
            print(f"[WebSocket] Reconnecting in {check_interval} seconds...")
            await asyncio.sleep(check_interval)


class MockWebSocketClient(WebSocketClient):
    """Mock WebSocket client for testing without backend"""
    
    async def connect(self) -> bool:
        print("[MockWebSocket] Mock connection (no backend)")
        self.connected = True
        return True
    
    async def send_board_update(self, update: BoardUpdate) -> bool:
        if update.fen == self.last_fen:
            return True
        
        self.last_fen = update.fen
        fen_display = update.fen[:30] if len(update.fen) > 30 else update.fen
        print(f"[MockWebSocket] Would send: FEN={fen_display}... conf={update.confidence:.2f}")
        return True
    
    async def disconnect(self):
        self.connected = False
        print("[MockWebSocket] Mock disconnected")
