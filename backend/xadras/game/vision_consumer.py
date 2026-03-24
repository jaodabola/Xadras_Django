import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)

class VisionConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for Vision Service communication"""
    
    async def connect(self):
        """Accept WebSocket connection"""
        self.vision_group_name = 'vision_updates'
        
        # Join vision group
        await self.channel_layer.group_add(
            self.vision_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Vision WebSocket connected: {self.channel_name}")
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Vision WebSocket connected successfully'
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave vision group
        await self.channel_layer.group_discard(
            self.vision_group_name,
            self.channel_name
        )
        logger.info(f"Vision WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data):
        """Handle messages from Vision Service"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            logger.info(f"Received vision message: {message_type}")
            
            if message_type == 'board_update':
                await self.handle_board_update(data)
            elif message_type == 'camera_status':
                await self.handle_camera_status(data)
            elif message_type == 'calibration_request':
                await self.handle_calibration_request(data)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received from Vision Service")
        except Exception as e:
            logger.error(f"Error processing vision message: {e}")

    async def handle_board_update(self, data):
        """Handle board state updates from Vision Service"""
        try:
            board_data = data.get('data', {})
            camera_id = board_data.get('camera_id')
            fen = board_data.get('fen')
            move = board_data.get('move')
            
            logger.info(f"Board update - Camera: {camera_id}, FEN: {fen}, Move: {move}")
            
            # Broadcast to game consumers if needed
            if camera_id and fen:
                await self.channel_layer.group_send(
                    f'game_camera_{camera_id}',
                    {
                        'type': 'board_state_update',
                        'camera_id': camera_id,
                        'fen': fen,
                        'move': move,
                        'timestamp': board_data.get('timestamp')
                    }
                )
            
            # Acknowledge receipt
            await self.send(text_data=json.dumps({
                'type': 'board_update_ack',
                'camera_id': camera_id,
                'status': 'received'
            }))
            
        except Exception as e:
            logger.error(f"Error handling board update: {e}")

    async def handle_camera_status(self, data):
        """Handle camera status updates"""
        try:
            status_data = data.get('data', {})
            camera_id = status_data.get('camera_id')
            status = status_data.get('status')
            
            logger.info(f"Camera status - ID: {camera_id}, Status: {status}")
            
            # Acknowledge receipt
            await self.send(text_data=json.dumps({
                'type': 'camera_status_ack',
                'camera_id': camera_id,
                'status': 'received'
            }))
            
        except Exception as e:
            logger.error(f"Error handling camera status: {e}")

    async def handle_calibration_request(self, data):
        """Handle calibration requests"""
        try:
            calibration_data = data.get('data', {})
            camera_id = calibration_data.get('camera_id')
            
            logger.info(f"Calibration request - Camera: {camera_id}")
            
            # Send calibration response
            await self.send(text_data=json.dumps({
                'type': 'calibration_response',
                'camera_id': camera_id,
                'action': 'start_calibration',
                'instructions': 'Please ensure the chessboard is visible and well-lit'
            }))
            
        except Exception as e:
            logger.error(f"Error handling calibration request: {e}")

    # Group message handlers
    async def vision_broadcast(self, event):
        """Handle broadcast messages to vision group"""
        await self.send(text_data=json.dumps(event['data']))

    async def camera_assignment(self, event):
        """Handle camera assignment messages"""
        await self.send(text_data=json.dumps({
            'type': 'camera_assignment',
            'data': event['data']
        }))
