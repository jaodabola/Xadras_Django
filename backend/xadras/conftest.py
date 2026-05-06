"""
Configuração partilhada para testes do Xadras.
Fixtures reutilizáveis para autenticação e criação de dados de teste.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def api_client():
    """Cliente da API sem autenticação."""
    return APIClient()


@pytest.fixture
def create_user(db):
    """Factory para criar utilizadores de teste."""
    def _create_user(username='testuser', password='TestPass123!', **kwargs):
        defaults = {
            'email': f'{username}@example.com',
            'elo_rating': 1200,
        }
        defaults.update(kwargs)
        user = User.objects.create_user(
            username=username, password=password, **defaults
        )
        return user
    return _create_user


@pytest.fixture
def user(create_user):
    """Utilizador autenticado padrão."""
    return create_user()


@pytest.fixture
def user2(create_user):
    """Segundo utilizador para testes que requerem dois jogadores."""
    return create_user(username='testuser2', elo_rating=1300)


@pytest.fixture
def guest_user(create_user):
    """Utilizador convidado."""
    return create_user(username='guest_abc123', is_guest=True)


@pytest.fixture
def auth_client(api_client, user):
    """Cliente da API autenticado com token."""
    token, _ = Token.objects.get_or_create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return api_client


@pytest.fixture
def auth_client2(user2):
    """Segundo cliente da API autenticado."""
    client = APIClient()
    token, _ = Token.objects.get_or_create(user=user2)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


@pytest.fixture
def guest_client(api_client, guest_user):
    """Cliente da API autenticado como convidado."""
    token, _ = Token.objects.get_or_create(user=guest_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return api_client
