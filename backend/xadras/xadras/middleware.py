# XADRAS - Rate Limiting Middleware
# Implementation based on Security AI configuration
# Priority: CRITICAL - Security requirement

from django.http import JsonResponse
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
import logging

logger = logging.getLogger(__name__)

class RateLimitMiddleware:
    """
    Middleware to handle rate limiting exceptions and provide consistent responses
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, Ratelimited):
            logger.warning(f"Rate limit exceeded for {request.META.get('REMOTE_ADDR')} on {request.path}")
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.',
                'retry_after': 60  # seconds
            }, status=429)
        return None

class WebSocketRateLimitMiddleware:
    """
    Custom middleware for WebSocket connection rate limiting
    Based on Security AI specifications
    """
    
    @staticmethod
    def check_connection_limit(user, ip_address):
        """Check if user/IP has exceeded WebSocket connection limits"""
        # Para utilizadores anónimos/guests, usar IP como identificador
        if user.is_authenticated:
            user_key = f"ws_connections_user_{user.id}"
        else:
            user_key = f"ws_connections_ip_{ip_address}"
        
        ip_key = f"ws_connections_ip_{ip_address}"
        
        user_connections = cache.get(user_key, 0)
        ip_connections = cache.get(ip_key, 0)
        
        # Limits
        MAX_CONNECTIONS_PER_USER = 10
        MAX_CONNECTIONS_PER_IP = 50
        
        if user_connections >= MAX_CONNECTIONS_PER_USER:
            return False, f"User connection limit exceeded ({MAX_CONNECTIONS_PER_USER})"
        
        if ip_connections >= MAX_CONNECTIONS_PER_IP:
            return False, f"IP connection limit exceeded ({MAX_CONNECTIONS_PER_IP})"
        
        return True, "Connection allowed"
    
    @staticmethod
    def increment_connection_count(user, ip_address):
        """Increment connection counters"""
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
        """Decrement connection counters"""
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

# Rate limiting decorators for common endpoints
def auth_rate_limit(view_func):
    """Rate limiting for authentication endpoints"""
    return ratelimit(key='ip', rate='5/m', method='POST', block=True)(view_func)

def game_rate_limit(view_func):
    """Rate limiting for game endpoints"""
    return ratelimit(key='user', rate='60/m', method='POST', block=False)(view_func)

def matchmaking_rate_limit(view_func):
    """Rate limiting for matchmaking endpoints"""
    return ratelimit(key='user', rate='20/m', method='POST', block=True)(view_func)

def tournament_rate_limit(view_func):
    """Rate limiting for tournament endpoints"""
    return ratelimit(key='user', rate='5/m', method='POST', block=True)(view_func)

def camera_rate_limit(view_func):
    """Rate limiting for camera endpoints"""
    return ratelimit(key='user', rate='2/m', method='POST', block=True)(view_func)
