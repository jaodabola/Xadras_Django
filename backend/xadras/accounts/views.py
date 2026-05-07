import uuid
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django_ratelimit.decorators import ratelimit

from .models import User


# Logger do módulo
logger = logging.getLogger(__name__)


class GuestView(APIView):
    """
    Cria um utilizador convidado (guest) temporário.
    Este utilizador é gerado automaticamente com um username único.
    """

    @method_decorator(ratelimit(key="ip", rate="15/m", method="POST", block=True))
    def post(self, request, *args, **kwargs):
        try:
            # Geração de nome único para o utilizador guest
            guest_name = f"guest_{uuid.uuid4().hex[:8]}"
            password = uuid.uuid4().hex

            # Criação do utilizador guest
            user = User.objects.create_user(
                username=guest_name,
                password=password,
                is_guest=True,
                email=f"{guest_name}@example.com",
            )

            # Criação do token de autenticação
            token, _ = Token.objects.get_or_create(user=user)

            return Response(
                {
                    "username": user.username,
                    "token": token.key,
                    "is_guest": True,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error("Erro ao criar utilizador guest", exc_info=True)

            return Response(
                {"error": "Falha ao criar utilizador guest"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserProfileView(APIView):
    """
    Retorna informações básicas do perfil do utilizador autenticado.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        return Response(
            {
                "username": user.username,
                "elo_rating": user.elo_rating,
                "games_played": user.games_played,
                "games_won": user.games_won,
                "games_lost": user.games_lost,
                "games_drawn": user.games_drawn,
            }
        )


class UserStatsView(APIView):
    """
    Retorna estatísticas detalhadas do utilizador autenticado.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        win_rate = user.get_win_rate()
        draw_rate = user.get_draw_rate()

        return Response(
            {
                "elo_rating": user.elo_rating,
                "games_played": user.games_played,
                "games_won": user.games_won,
                "games_lost": user.games_lost,
                "games_drawn": user.games_drawn,
                "win_rate": win_rate,
                "draw_rate": draw_rate,
            }
        )


class CSRFTokenView(APIView):
    """
    Endpoint utilizado para garantir que o cookie CSRF é definido no cliente.
    Necessário para chamadas autenticadas via browser.
    """

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        return Response(
            {"detail": "CSRF cookie definido"},
            status=status.HTTP_200_OK,
        )


class GuestDeleteView(APIView):
    """
    Permite que um utilizador guest elimine a sua própria conta.
    Utilizado para remover contas temporárias após terminar uma sessão.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        user = request.user

        logger.info(
            f"Tentativa de remoção de conta guest: {user.username} (ID: {user.id})"
        )

        # Apenas utilizadores guest podem usar este endpoint
        if not getattr(user, "is_guest", False):
            logger.warning(
                f"Utilizador não guest tentou remover conta: {user.username}"
            )

            return Response(
                {"error": "Apenas utilizadores guest podem usar este endpoint"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            user.delete()

            logger.info(
                f"Conta guest removida com sucesso: {user.username} (ID: {user.id})"
            )

            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception:
            logger.error(
                "Erro ao remover utilizador guest",
                exc_info=True,
            )

            return Response(
                {"error": "Falha ao remover utilizador guest"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
