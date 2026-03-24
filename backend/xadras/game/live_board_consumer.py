"""
Consumer WebSocket para deteção de tabuleiro em direto.

Versão simplificada: o browser liga-se a este WebSocket com um
session_id e fica à escuta. A app do telemóvel envia o FEN via
endpoint REST (LiveBoardFenView), que faz broadcast para aqui.

Já não processa frames de vídeo no servidor.
"""

import json
import logging
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class LiveBoardConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket para o modo câmara do tabuleiro.

    Protocolo:
        1. Browser liga-se com: ws://host/ws/live-board/?session=<session_id>
        2. App do telemóvel envia FEN via POST /api/game/live-board/fen/
        3. O servidor retransmite o FEN para o browser através deste consumer.

    Mensagens enviadas ao browser:
        { "type": "detection_result", "fen": "...", "board_detected": true, ... }
    """

    async def connect(self):
        """Aceitar ligação e juntar ao grupo de sessão."""
        # Extrair session_id dos query params
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        params = parse_qs(query_string)
        self.session_id = params.get('session', [''])[0]

        if not self.session_id:
            # Sem session_id — recusar ligação
            logger.warning('LiveBoard WS ligação recusada: session_id em falta')
            await self.close(code=4000)
            return

        # Nome do grupo = live_board_<session_id>
        self.group_name = f'live_board_{self.session_id}'

        # Juntar ao grupo do channel layer
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()
        logger.info(
            f'LiveBoard WS conectado: {self.channel_name} '
            f'(sessão: {self.session_id})'
        )

        # Mensagem de boas-vindas
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Ligação ao detetor de tabuleiro estabelecida',
            'session_id': self.session_id,
        }))

    async def disconnect(self, close_code):
        """Remover do grupo ao desconectar."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )
        logger.info(f'LiveBoard WS desconectado: {self.channel_name}')

    async def receive(self, text_data):
        """
        Processar mensagens recebidas do browser.

        Nesta versão simplificada apenas suportamos 'ping'.
        Frames de vídeo já não são processados no servidor.
        """
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')

            if msg_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            else:
                logger.debug(f'Tipo de mensagem ignorado: {msg_type}')

        except json.JSONDecodeError:
            logger.error('JSON inválido recebido no LiveBoardConsumer')

    # ---- Handlers para mensagens do channel layer ----

    async def fen_update(self, event):
        """
        Recebe broadcast do LiveBoardFenView e envia ao browser.

        Formato enviado ao browser:
            {
                "type": "detection_result",
                "board_detected": true,
                "fen": "<FEN normalizado>",
                "session_id": "...",
                "utilizador": "..."
            }
        """
        await self.send(text_data=json.dumps({
            'type': 'detection_result',
            'board_detected': event.get('board_detected', True),
            'fen': event.get('fen', ''),
            'session_id': event.get('session_id', ''),
            'utilizador': event.get('utilizador', ''),
        }))
