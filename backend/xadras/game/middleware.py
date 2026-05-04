import urllib.parse
from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async


@database_sync_to_async
def get_user_from_token(token_key):
    from django.contrib.auth.models import AnonymousUser
    from rest_framework.authtoken.models import Token
    try:
        token = Token.objects.get(key=token_key)
        return token.user
    except Token.DoesNotExist:
        return AnonymousUser()


class TokenAuthMiddleware:
    """
    Middleware personalizado que extrai o token do DRF da string de consulta.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        from django.contrib.auth.models import AnonymousUser
        query_string = scope.get("query_string", b"").decode()
        query_params = urllib.parse.parse_qs(query_string)

        # Procura for parametro do token
        token_key = query_params.get("token", [None])[0]

        if token_key:
            scope["user"] = await get_user_from_token(token_key)
        else:
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)


def TokenAuthMiddlewareStack(inner):
    return TokenAuthMiddleware(AuthMiddlewareStack(inner))
