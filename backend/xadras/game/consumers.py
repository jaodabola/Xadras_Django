from channels.generic.websocket import AsyncWebsocketConsumer
import json
from .models import Game, Move
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from xadras.middleware import WebSocketRateLimitMiddleware
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f'game_{self.game_id}'

        # Get user and IP for rate limiting
        user = self.scope.get('user')
        ip_address = self.scope.get('client', ['unknown', None])[0]

        # Check WebSocket connection limits
        allowed, message = WebSocketRateLimitMiddleware.check_connection_limit(
            user, ip_address)
        if not allowed:
            logger.warning(
                f"WebSocket connection denied: {message} for user {user} from {ip_address}")
            await self.close(code=4429)  # Custom close code for rate limit
            return

        # Increment connection count
        WebSocketRateLimitMiddleware.increment_connection_count(
            user, ip_address)
        self.user = user
        self.ip_address = ip_address

        # Join game group
        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )

        logger.info(
            f"WebSocket connected: user {user} from {ip_address} to game {self.game_id}")
        await self.accept()

    async def disconnect(self, close_code):
        # Decrement connection count
        if hasattr(self, 'user') and hasattr(self, 'ip_address'):
            WebSocketRateLimitMiddleware.decrement_connection_count(
                self.user, self.ip_address)
            logger.info(
                f"WebSocket disconnected: user {self.user} from {self.ip_address}")

        # Leave game group
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)

        if data['type'] == 'move':
            await self.handle_move(data)
        elif data['type'] == 'chat':
            await self.handle_chat(data)
        elif data['type'] == 'board_update':
            await self.handle_board_update(data)
        elif data['type'] == 'resign':
            await self.handle_resign(data)

    async def handle_move(self, data):
        try:
            # Broadcast move to all clients in the game group without modifying the database.
            # The REST /game/{id}/move/ endpoint remains the single source of truth for
            # persisting moves and updating FEN/turn state.
            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'game_move',
                    'move': {
                        'san': data['move_san'],
                        'fen': data['fen_after']
                    }
                }
            )
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def handle_chat(self, data):
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'chat_message',
                'message': data['message'],
                'user': self.scope['user'].username
            }
        )

    async def handle_board_update(self, data):
        """
        Handle board_update message from Vision AI
        Format: { "type":"board_update", "uci_list":["e2e4"], "fen":"...", "confidence":0.9 }
        """
        try:
            # Validate required fields
            required_fields = ['uci_list', 'fen', 'confidence']
            for field in required_fields:
                if field not in data:
                    logger.error(
                        f"Missing required field in board_update: {field}")
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': f'Missing required field: {field}'
                    }))
                    return

            uci_list = data['uci_list']
            fen = data['fen']
            confidence = data['confidence']

            # Validate confidence threshold (configurable)
            MIN_CONFIDENCE = 0.7
            if confidence < MIN_CONFIDENCE:
                logger.warning(
                    f"Board update confidence too low: {confidence} < {MIN_CONFIDENCE}")
                await self.send(text_data=json.dumps({
                    'type': 'board_update_rejected',
                    'reason': 'confidence_too_low',
                    'confidence': confidence,
                    'min_confidence': MIN_CONFIDENCE
                }))
                return

            # Get game and validate
            game = await Game.objects.aget(id=self.game_id)
            if game.status != 'IN_PROGRESS':
                logger.warning(
                    f"Board update for non-active game: {self.game_id}")
                return

            # Process UCI moves (Vision AI detected moves)
            if uci_list:
                # For now, we'll broadcast the board update to all clients
                # The frontend can decide how to handle it (show suggestions, auto-move, etc.)
                await self.channel_layer.group_send(
                    self.game_group_name,
                    {
                        'type': 'board_update_message',
                        'uci_list': uci_list,
                        'fen': fen,
                        'confidence': confidence,
                        'timestamp': data.get('timestamp'),
                        'camera_id': data.get('camera_id')
                    }
                )

                logger.info(
                    f"Board update processed for game {self.game_id}: {uci_list} (confidence: {confidence})")

            # Optionally, auto-validate moves if confidence is very high
            AUTO_MOVE_CONFIDENCE = 0.95
            if confidence >= AUTO_MOVE_CONFIDENCE and len(uci_list) == 1:
                # High confidence single move - could auto-apply
                # For now, just log it - implementation depends on game rules
                logger.info(
                    f"High confidence move detected: {uci_list[0]} (confidence: {confidence})")

        except Exception as e:
            logger.error(
                f"Error handling board_update: {str(e)}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Board update processing failed: {str(e)}'
            }))

    # Receive move from game group
    async def game_move(self, event):
        move = event['move']
        await self.send(text_data=json.dumps({
            'type': 'move',
            'move': move
        }))

    # Receive chat message from game group
    async def chat_message(self, event):
        message = event['message']
        user = event['user']
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': message,
            'user': user
        }))

    # Receive board update from Vision AI
    async def board_update_message(self, event):
        """Send board update to connected clients"""
        await self.send(text_data=json.dumps({
            'type': 'board_update',
            'uci_list': event['uci_list'],
            'fen': event['fen'],
            'confidence': event['confidence'],
            'timestamp': event.get('timestamp'),
            'camera_id': event.get('camera_id')
        }))

    async def handle_resign(self, data):
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'game_resign',
                'color': data.get('color'),
                'reason': data.get('reason')
            }
        )

    async def game_resign(self, event):
        await self.send(text_data=json.dumps({
            'type': 'resign',
            'color': event.get('color'),
            'reason': event.get('reason')
        }))
