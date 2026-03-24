"""
Vista REST para receber FEN de uma app externa (telemóvel).

Endpoint leve que valida o FEN com python-chess e faz broadcast
via channel layer para o browser que esteja a escutar na sessão.
"""

import logging

import chess
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

logger = logging.getLogger(__name__)


class LiveBoardFenView(APIView):
    """
    POST /api/game/live-board/fen/

    Recebe um FEN enviado por uma app externa (ex.: telemóvel),
    valida-o e retransmite para o browser ligado à mesma sessão.

    Body esperado:
        {
            "fen": "<string FEN válido>",
            "session_id": "<identificador da sessão>"
        }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        fen = request.data.get('fen', '').strip()
        session_id = request.data.get('session_id', '').strip()

        # --- Validação dos campos obrigatórios ---
        if not fen:
            return Response(
                {'erro': 'O campo "fen" é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not session_id:
            return Response(
                {'erro': 'O campo "session_id" é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- Validação do FEN com python-chess ---
        try:
            board = chess.Board(fen)
        except ValueError:
            return Response(
                {'erro': 'FEN inválido.', 'fen_recebido': fen},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- Broadcast via channel layer para o browser ---
        channel_layer = get_channel_layer()
        grupo = f'live_board_{session_id}'

        try:
            async_to_sync(channel_layer.group_send)(
                grupo,
                {
                    'type': 'fen_update',
                    'fen': board.fen(),        # FEN normalizado
                    'board_detected': True,
                    'session_id': session_id,
                    'utilizador': request.user.username,
                },
            )
        except Exception as e:
            logger.error(f'Erro ao enviar FEN para o grupo {grupo}: {e}')
            return Response(
                {'erro': 'Falha ao retransmitir o FEN.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            f'FEN recebido de {request.user.username} '
            f'para sessão {session_id}: {board.fen()}'
        )

        return Response(
            {
                'mensagem': 'FEN recebido e retransmitido com sucesso.',
                'fen': board.fen(),
                'session_id': session_id,
            },
            status=status.HTTP_200_OK,
        )
