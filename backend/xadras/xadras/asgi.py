import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xadras.settings')

# 1. Inicializar o Django primeiro!
# Isso preenche o AppRegistry e permite importar modelos depois.
django_asgi_app = get_asgi_application()

# 2. Agora sim podemos importar o código que usa modelos
from game.middleware import TokenAuthMiddlewareStack
from game import routing as game_routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        TokenAuthMiddlewareStack(
            URLRouter(
                game_routing.websocket_urlpatterns
            )
        )
    ),
})
