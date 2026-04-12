# XADRAS - Middleware de Rate Limiting
# Implementação baseada na configuração de IA de Segurança
# Prioridade: CRÍTICA - Requisito de segurança

from django.http import JsonResponse
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Middleware para lidar com exceções de limite de taxa (rate limiting) e fornecer respostas consistentes
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, Ratelimited):
            logger.warning(
                f"Limite de taxa excedido para {request.META.get('REMOTE_ADDR')} em {request.path}")
            return JsonResponse({
                'error': 'Limite de taxa excedido',
                'message': 'Demasiados pedidos. Por favor, tente novamente mais tarde.',
                'retry_after': 60  # segundos
            }, status=429)
        return None


class WebSocketRateLimitMiddleware:
    """
    Middleware personalizado para limite de taxa de ligação WebSocket
    Baseado nas especificações da IA de Segurança
    """

    @staticmethod
    def check_connection_limit(user, ip_address):
        """Verificar se o utilizador/IP excedeu os limites de ligação WebSocket"""
        # Para utilizadores anónimos/guests, usar IP como identificador
        if user.is_authenticated:
            user_key = f"ws_connections_user_{user.id}"
        else:
            user_key = f"ws_connections_ip_{ip_address}"

        ip_key = f"ws_connections_ip_{ip_address}"

        user_connections = cache.get(user_key, 0)
        ip_connections = cache.get(ip_key, 0)

        # Limites
        MAX_CONNECTIONS_PER_USER = 10
        MAX_CONNECTIONS_PER_IP = 50

        if user_connections >= MAX_CONNECTIONS_PER_USER:
            return False, f"Limite de ligação do utilizador excedido ({MAX_CONNECTIONS_PER_USER})"

        if ip_connections >= MAX_CONNECTIONS_PER_IP:
            return False, f"Limite de ligação de IP excedido ({MAX_CONNECTIONS_PER_IP})"

        return True, "Ligação permitida"

    @staticmethod
    def increment_connection_count(user, ip_address):
        """Incrementar contadores de ligação"""
        if user.is_authenticated:
            user_key = f"ws_connections_user_{user.id}"
        else:
            user_key = f"ws_connections_ip_{ip_address}"
        ip_key = f"ws_connections_ip_{ip_address}"

        # TTL curto (5 min) para evitar contadores stale após reiniciar servidor
        cache.set(user_key, cache.get(user_key, 0) + 1, 300)
        cache.set(ip_key, cache.get(ip_key, 0) + 1, 300)

    @staticmethod
    def decrement_connection_count(user, ip_address):
        """Decrementar contadores de ligação"""
        if user.is_authenticated:
            user_key = f"ws_connections_user_{user.id}"
        else:
            user_key = f"ws_connections_ip_{ip_address}"
        ip_key = f"ws_connections_ip_{ip_address}"

        user_count = max(0, cache.get(user_key, 0) - 1)
        ip_count = max(0, cache.get(ip_key, 0) - 1)

        if user_count > 0:
            cache.set(user_key, user_count, 300)
        else:
            cache.delete(user_key)

        if ip_count > 0:
            cache.set(ip_key, ip_count, 300)
        else:
            cache.delete(ip_key)

# Decoradores de limite de taxa para endpoints comuns


def auth_rate_limit(view_func):
    """Limite de taxa para endpoints de autenticação"""
    return ratelimit(key='ip', rate='5/m', method='POST', block=True)(view_func)


def game_rate_limit(view_func):
    """Limite de taxa para endpoints de jogo"""
    return ratelimit(key='user', rate='60/m', method='POST', block=False)(view_func)


def matchmaking_rate_limit(view_func):
    """Limite de taxa para endpoints de matchmaking"""
    return ratelimit(key='user', rate='20/m', method='POST', block=True)(view_func)


def tournament_rate_limit(view_func):
    """Limite de taxa para endpoints de torneio"""
    return ratelimit(key='user', rate='5/m', method='POST', block=True)(view_func)
