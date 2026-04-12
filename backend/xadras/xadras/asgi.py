"""
Configuração ASGI para o projeto xadras.

Expõe o chamável ASGI como uma variável de nível de módulo chamada ``application``.

Para mais informações sobre este ficheiro, consulte
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from game.middleware import TokenAuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xadras.settings')

# Inicializar a aplicação ASGI do Django cedo para garantir que o AppRegistry
# seja preenchido antes de importar código que possa importar modelos ORM.
django_asgi_app = get_asgi_application()

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
