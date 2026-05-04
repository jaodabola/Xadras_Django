"""
Consumer WebSocket para deteção de tabuleiro em direto.

O browser liga-se com um session_id e fica à escuta.
A app do telemóvel envia FEN via WebSocket, que é retransmitido
para o browser e guardado na BD para revisão futura.
"""

import json
import logging
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class LiveBoardConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket para o modo câmara do tabuleiro.

    Protocolo:
        1. Browser liga-se com: ws://host/ws/live-board/?session=<session_id>
        2. App do telemóvel envia FEN via WebSocket (type: fen_update)
        3. O servidor guarda o move na BD e retransmite para o browser.

    Mensagens enviadas ao browser:
        { "type": "detection_result", "fen": "...", "board_detected": true, ... }
    """

    async def connect(self):
        """Aceitar ligação e juntar ao grupo de sessão."""
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        params = parse_qs(query_string)
        self.session_id = params.get('session', [''])[0]

        if not self.session_id:
            logger.warning('LiveBoard WS ligação recusada: session_id em falta')
            await self.close(code=4000)
            return

        self.group_name = f'live_board_{self.session_id}'
        self.game_id = None       # Será criado no primeiro FEN
        self.last_fen = None      # Último FEN guardado (evitar duplicados)

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()
        logger.info(
            f'LiveBoard WS conectado: {self.channel_name} '
            f'(sessão: {self.session_id})'
        )

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
        Processar mensagens recebidas via WebSocket.

        Fluxo otimizado para baixa latência:
          1. Validar e fazer broadcast ao browser IMEDIATAMENTE
          2. Persistir na BD em background (não bloqueia o broadcast)

        Suporta:
        - 'ping': keep-alive
        - 'fen_update': FEN enviado pelo telemóvel → broadcast instantâneo + guardar
        """
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')

            if msg_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))

            elif msg_type == 'fen_update':
                fen = data.get('fen', '').strip()
                if not fen or fen == self.last_fen:
                    return  # Ignorar duplicados

                self.last_fen = fen
                user = self.scope.get('user')

                # ── PASSO 1: Broadcast imediato ao browser (sem esperar pela BD) ──
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'fen_update',
                        'fen': fen,
                        'board_detected': True,
                        'session_id': self.session_id,
                        'game_id': self.game_id,  # Pode ser None no primeiro move
                        'utilizador': user.username if user and hasattr(user, 'username') else '',
                    },
                )

                # ── PASSO 2: Persistir na BD em background (não bloqueia o WS) ──
                import asyncio
                asyncio.ensure_future(self._persist_fen_background(fen, user))

            else:
                logger.debug(f'Tipo de mensagem ignorado: {msg_type}')

        except json.JSONDecodeError:
            logger.error('JSON inválido recebido no LiveBoardConsumer')

    async def _persist_fen_background(self, fen, user):
        """Persistir FEN na BD sem bloquear o fluxo principal do WebSocket."""
        try:
            await self._persist_fen(fen, user)
        except Exception as e:
            logger.error(f'Erro ao persistir FEN em background: {e}')

    # ---- Persistência na BD ----

    @database_sync_to_async
    def _persist_fen(self, fen, user):
        """
        Guardar FEN na BD com suporte a takebacks.
        """
        from .models import Game, Move
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # 1. Criar Game se necessário
        if self.game_id is None:
            game = Game.objects.create(
                white_player=user if user and user.is_authenticated else User.objects.first(),
                status='IN_PROGRESS',
                game_type='LIVE_CAPTURE',
                time_control='unlimited',
                fen_string=fen,
            )
            self.game_id = game.id
            logger.info(f'Game #{game.id} criado para sessão {self.session_id}')
            return self.game_id

        game = Game.objects.get(id=self.game_id)

        # 2. Verificar se é um takeback (FEN já existe na história)
        existing_move = (
            Move.objects
            .filter(game=game, fen_after=fen)
            .order_by('move_number')
            .first()
        )

        if existing_move:
            # É um takeback! Apagar todos os moves após este
            deleted, _ = (
                Move.objects
                .filter(game=game, move_number__gt=existing_move.move_number)
                .delete()
            )
            game.fen_string = fen
            game.save(update_fields=['fen_string', 'updated_at'])
            logger.info(
                f'Game #{game.id}: Takeback para move {existing_move.move_number} '
                f'({deleted} moves apagados)'
            )
            return self.game_id

        # Verificar se é o FEN inicial (posição padrão) e ainda não há moves
        starting_fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        if fen == starting_fen and not Move.objects.filter(game=game).exists():
            game.fen_string = fen
            game.save(update_fields=['fen_string', 'updated_at'])
            return self.game_id

        # 3. Novo move — calcular número seguinte
        last_move_num = (
            Move.objects
            .filter(game=game)
            .order_by('-move_number')
            .values_list('move_number', flat=True)
            .first()
        ) or 0

        Move.objects.create(
            game=game,
            move_number=last_move_num + 1,
            move_san=f'move{last_move_num + 1}',  # Placeholder (sem SAN real)
            fen_after=fen,
        )

        game.fen_string = fen
        game.save(update_fields=['fen_string', 'updated_at'])

        logger.debug(f'Game #{game.id}: Move {last_move_num + 1} guardado')
        return self.game_id

    # ---- Handlers para mensagens do channel layer ----

    async def fen_update(self, event):
        """Recebe broadcast e envia ao browser."""
        await self.send(text_data=json.dumps({
            'type': 'detection_result',
            'board_detected': event.get('board_detected', True),
            'fen': event.get('fen', ''),
            'session_id': event.get('session_id', ''),
            'game_id': event.get('game_id'),
            'utilizador': event.get('utilizador', ''),
        }))
