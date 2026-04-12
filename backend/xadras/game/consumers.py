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

        # Obter o utilizador e o IP para limitação de taxa (rate limiting)
        user = self.scope.get('user')
        ip_address = self.scope.get('client', ['unknown', None])[0]

        # Verificar os limites de ligação WebSocket
        allowed, message = WebSocketRateLimitMiddleware.check_connection_limit(
            user, ip_address)
        if not allowed:
            logger.warning(
                f"WebSocket connection denied: {message} for user {user} from {ip_address}")
            await self.close(code=4429)  # Código de fecho personalizado para limite de taxa
            return

        # Incrementar a contagem de ligações
        WebSocketRateLimitMiddleware.increment_connection_count(
            user, ip_address)
        self.user = user
        self.ip_address = ip_address

        # Juntar ao grupo do jogo
        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )

        logger.info(
            f"WebSocket connected: user {user} from {ip_address} to game {self.game_id}")
        await self.accept()

    async def disconnect(self, close_code):
        # Decrementar a contagem de ligações
        if hasattr(self, 'user') and hasattr(self, 'ip_address'):
            WebSocketRateLimitMiddleware.decrement_connection_count(
                self.user, self.ip_address)
            logger.info(
                f"WebSocket disconnected: user {self.user} from {self.ip_address}")

        # Sair do grupo do jogo
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )

    # Receber mensagem do WebSocket
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
            # Transmitir a jogada para todos os clientes no grupo do jogo sem modificar a base de dados.
            # O endpoint REST /game/{id}/move/ continua a ser a única fonte de verdade para
            # persistir jogadas e atualizar o estado do FEN/vez de jogar.
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
        Lidar com a mensagem board_update da IA de Visão
        Formato: { "type":"board_update", "uci_list":["e2e4"], "fen":"...", "confidence":0.9 }
        """
        try:
            # Validar campos obrigatórios
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

            # Validar o limite de confiança (configurável)
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

            # Obter o jogo e validar
            game = await Game.objects.aget(id=self.game_id)
            if game.status != 'IN_PROGRESS':
                logger.warning(
                    f"Board update for non-active game: {self.game_id}")
                return

            # Processar jogadas UCI (jogadas detetadas pela IA de Visão)
            if uci_list:
                # Por agora, vamos transmitir a atualização do tabuleiro para todos os clientes
                # O frontend pode decidir como lidar com isso (mostrar sugestões, auto-jogada, etc.)
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

            # Opcionalmente, validar automaticamente as jogadas se a confiança for muito alta
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

    # Receber jogada do grupo do jogo
    async def game_move(self, event):
        move = event['move']
        await self.send(text_data=json.dumps({
            'type': 'move',
            'move': move
        }))

    # Receber mensagem de chat do grupo do jogo
    async def chat_message(self, event):
        message = event['message']
        user = event['user']
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': message,
            'user': user
        }))

    # Receber atualização do tabuleiro da IA de Visão
    async def board_update_message(self, event):
        """Enviar atualização do tabuleiro para os clientes ligados"""
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
