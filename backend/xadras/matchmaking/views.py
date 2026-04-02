import logging
import random

from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication

from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from .models import MatchmakingQueue
from .serializers import MatchmakingQueueSerializer
from game.models import Game

logger = logging.getLogger("matchmaking.views")


class MatchmakingView(APIView):
    """
    View principal do sistema de matchmaking.

    Endpoints:
    GET -> ver estado da fila
    POST -> entrar na fila
    DELETE -> sair da fila
    """

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    # ------------------------------------------------
    # Ver estado da fila
    # ------------------------------------------------

    def get(self, request):

        try:
            entry = MatchmakingQueue.objects.get(user=request.user)

            serializer = MatchmakingQueueSerializer(entry)

            return Response(serializer.data)

        except MatchmakingQueue.DoesNotExist:

            return Response({"in_queue": False})

    # ------------------------------------------------
    # Entrar na fila
    # ------------------------------------------------

    @method_decorator(ratelimit(key="user", rate="20/m", method="POST", block=True))
    def post(self, request):

        user = request.user
        preferred_color = request.data.get("preferred_color", "ANY").upper()
        time_control = request.data.get("time_control", "rapid").lower()

        if preferred_color not in ["WHITE", "BLACK", "ANY"]:
            return Response(
                {"error": "Preferência de cor inválida"},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        if time_control not in ["bullet", "blitz", "rapid", "classical", "unlimited"]:
            return Response(
                {"error": "Ritmo de jogo inválido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Remove entrada antiga
        MatchmakingQueue.objects.filter(user=user).delete()

        rating = getattr(user, "elo_rating", 1200)

        queue_entry = MatchmakingQueue.objects.create(
            user=user,
            rating=rating,
            preferred_color=preferred_color,
            time_control=time_control,
            joined_at=timezone.now(),
        )

        logger.info(f"{user.username} entrou na fila")

        opponent = self.find_opponent(queue_entry)

        if opponent:
            return self.create_match(queue_entry, opponent)

        return Response(
            {
                "status": "queued",
                "queue_id": queue_entry.id,
                "rating": rating,
                "preferred_color": preferred_color,
            },
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------
    # Sair da fila
    # ------------------------------------------------

    def delete(self, request):

        deleted, _ = MatchmakingQueue.objects.filter(
            user=request.user).delete()

        return Response(
            {"status": "left_queue" if deleted else "not_in_queue"},
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------
    # Encontrar oponente
    # ------------------------------------------------

    def find_opponent(self, entry):

        others = MatchmakingQueue.objects.filter(
            time_control=entry.time_control
        ).exclude(user=entry.user)

        for opponent in others:

            if (
                entry.preferred_color == "ANY"
                or opponent.preferred_color == "ANY"
                or entry.preferred_color != opponent.preferred_color
            ):
                return opponent

        return None

    # ------------------------------------------------
    # Criar jogo
    # ------------------------------------------------

    def create_match(self, player1, player2):

        user1 = player1.user
        user2 = player2.user

        color = random.choice(["WHITE", "BLACK"])

        white = user1 if color == "WHITE" else user2
        black = user2 if color == "WHITE" else user1

        game = Game.objects.create(
            white_player=white,
            black_player=black,
            status="IN_PROGRESS",
            time_control=player1.time_control,
        )

        MatchmakingQueue.objects.filter(
            user__in=[user1, user2]
        ).delete()

        logger.info(
            f"Match criado: {white.username} vs {black.username} | Game {game.id}"
        )

        return Response(
            {
                "status": "match_found",
                "game_id": game.id,
                "white": white.username,
                "black": black.username,
            }
        )
