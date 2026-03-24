from django.urls import re_path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from game.routing import websocket_urlpatterns as game_websocket_urlpatterns

# WebSocket URL patterns for testing
websocket_urlpatterns = game_websocket_urlpatterns

# Main application routing
application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            game_websocket_urlpatterns
        )
    ),
})
