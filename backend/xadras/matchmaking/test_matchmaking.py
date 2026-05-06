"""
Testes para a app Matchmaking.
Cobre: entrar na fila, sair da fila, verificar estado, encontrar oponente, criação de match.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from matchmaking.models import MatchmakingQueue
from game.models import Game
from django.contrib.auth import get_user_model

User = get_user_model()


# ============================================================
# Testes de Entrada na Fila
# ============================================================

@pytest.mark.django_db
class TestMatchmakingJoinQueue:
    """Testa o endpoint POST /api/matchmaking/"""

    def test_join_queue(self, auth_client, user):
        """Utilizador autenticado pode entrar na fila."""
        url = reverse('matchmaking')
        response = auth_client.post(url, {
            'preferred_color': 'ANY',
            'time_control': 'rapid',
        }, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'queued'
        assert MatchmakingQueue.objects.filter(user=user).exists()

    def test_join_queue_unauthenticated(self, api_client):
        """Utilizador não autenticado não pode entrar na fila."""
        url = reverse('matchmaking')
        response = api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_join_queue_invalid_color(self, auth_client):
        """Cor inválida deve devolver 400."""
        url = reverse('matchmaking')
        response = auth_client.post(url, {
            'preferred_color': 'PURPLE',
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_join_queue_invalid_time_control(self, auth_client):
        """Ritmo de jogo inválido deve devolver 400."""
        url = reverse('matchmaking')
        response = auth_client.post(url, {
            'time_control': 'hyper_bullet',
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_rejoin_queue_removes_old_entry(self, auth_client, user):
        """Reentrar na fila deve remover a entrada anterior."""
        url = reverse('matchmaking')
        auth_client.post(url, {'time_control': 'rapid'}, format='json')
        auth_client.post(url, {'time_control': 'blitz'}, format='json')

        entries = MatchmakingQueue.objects.filter(user=user)
        assert entries.count() == 1
        assert entries.first().time_control == 'blitz'


# ============================================================
# Testes de Estado da Fila
# ============================================================

@pytest.mark.django_db
class TestMatchmakingQueueStatus:
    """Testa o endpoint GET /api/matchmaking/"""

    def test_not_in_queue(self, auth_client):
        """Utilizador que não está na fila deve receber in_queue: False."""
        url = reverse('matchmaking')
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['in_queue'] is False

    def test_in_queue_returns_data(self, auth_client, user):
        """Utilizador na fila deve ver os seus dados."""
        MatchmakingQueue.objects.create(
            user=user, rating=1200, preferred_color='ANY', time_control='rapid'
        )

        url = reverse('matchmaking')
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'preferred_color' in response.data


# ============================================================
# Testes de Saída da Fila
# ============================================================

@pytest.mark.django_db
class TestMatchmakingLeaveQueue:
    """Testa o endpoint DELETE /api/matchmaking/"""

    def test_leave_queue(self, auth_client, user):
        """Utilizador pode sair da fila."""
        MatchmakingQueue.objects.create(
            user=user, rating=1200, preferred_color='ANY', time_control='rapid'
        )

        url = reverse('matchmaking')
        response = auth_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'left_queue'
        assert not MatchmakingQueue.objects.filter(user=user).exists()

    def test_leave_queue_not_in_queue(self, auth_client):
        """Sair da fila sem estar nela deve devolver 'not_in_queue'."""
        url = reverse('matchmaking')
        response = auth_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'not_in_queue'


# ============================================================
# Testes de Matching (Encontrar Oponente)
# ============================================================

@pytest.mark.django_db
class TestMatchmakingMatching:
    """Testa a lógica de emparelhamento automático."""

    def test_match_found_when_opponent_in_queue(self, auth_client, auth_client2, user, user2):
        """Se dois jogadores estão na fila com o mesmo ritmo, devem ser emparelhados."""
        url = reverse('matchmaking')

        # User1 entra na fila
        auth_client.post(url, {'time_control': 'rapid'}, format='json')

        # User2 entra — deve encontrar match
        response = auth_client2.post(url, {'time_control': 'rapid'}, format='json')

        assert response.data['status'] == 'match_found'
        assert 'game_id' in response.data

        # Verificar que o jogo foi criado
        game = Game.objects.get(id=response.data['game_id'])
        assert game.status == 'IN_PROGRESS'

    def test_no_match_different_time_controls(self, auth_client, auth_client2):
        """Jogadores com ritmos diferentes não devem ser emparelhados."""
        url = reverse('matchmaking')

        auth_client.post(url, {'time_control': 'rapid'}, format='json')
        response = auth_client2.post(url, {'time_control': 'bullet'}, format='json')

        assert response.data['status'] == 'queued'

    def test_match_clears_queue(self, auth_client, auth_client2, user, user2):
        """Após um match, ambos os jogadores devem ser removidos da fila."""
        url = reverse('matchmaking')

        auth_client.post(url, {'time_control': 'blitz'}, format='json')
        auth_client2.post(url, {'time_control': 'blitz'}, format='json')

        assert MatchmakingQueue.objects.filter(user=user).count() == 0
        assert MatchmakingQueue.objects.filter(user=user2).count() == 0

    def test_color_preference_respected(self, auth_client, auth_client2, user, user2):
        """As preferências de cor devem ser respeitadas."""
        url = reverse('matchmaking')

        auth_client.post(url, {
            'preferred_color': 'WHITE', 'time_control': 'rapid'
        }, format='json')

        response = auth_client2.post(url, {
            'preferred_color': 'BLACK', 'time_control': 'rapid'
        }, format='json')

        assert response.data['status'] == 'match_found'
        assert response.data['white'] == user.username
        assert response.data['black'] == user2.username
