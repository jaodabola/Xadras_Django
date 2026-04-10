"""
Vista REST para receber FEN de uma app externa (telemóvel).

Endpoint leve que retransmite o FEN via channel layer para o
browser que esteja a escutar na sessão.

A validação do FEN é feita no Android (chesslib) — aqui apenas
verificamos campos obrigatórios e retransmitimos sem delay.
"""

import logging

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

logger = logging.getLogger(__name__)


class LiveBoardFenView(APIView):
    """
    POST /api/game/live-board/fen/

    Recebe um FEN já validado pelo Android e retransmite
    imediatamente para o browser ligado à mesma sessão.

    Body esperado:
        {
            "fen": "<string FEN>",
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

        # --- Broadcast direto via channel layer (sem re-validação) ---
        channel_layer = get_channel_layer()
        grupo = f'live_board_{session_id}'

        try:
            async_to_sync(channel_layer.group_send)(
                grupo,
                {
                    'type': 'fen_update',
                    'fen': fen,
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
            f'FEN relay: {request.user.username} '
            f'→ sessão {session_id}: {fen}'
        )

        return Response(
            {
                'mensagem': 'FEN retransmitido com sucesso.',
                'fen': fen,
                'session_id': session_id,
            },
            status=status.HTTP_200_OK,
        )
