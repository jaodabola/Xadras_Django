from .settings import *

# Definições específicas para desenvolvimento local (Sem HTTPS)
DEBUG = True

# Desativar CSRF apenas para desenvolvimento local para evitar erros 403 em localhost
if 'django.middleware.csrf.CsrfViewMiddleware' in MIDDLEWARE:
    MIDDLEWARE.remove('django.middleware.csrf.CsrfViewMiddleware')

# Garantir que as origens de desenvolvimento são confiáveis
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://backend:8000',
]

CORS_ALLOWED_ORIGINS = CSRF_TRUSTED_ORIGINS

# Remover SessionAuthentication em dev para evitar que o DRF exija CSRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
}

# Desativar segurança de cookies
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = None
SESSION_COOKIE_SAMESITE = None

