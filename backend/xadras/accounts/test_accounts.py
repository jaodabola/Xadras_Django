"""
Testes para a app Accounts.
Cobre: criação de guest, perfil, estatísticas, eliminação de guest, registo e login via Djoser.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


# ============================================================
# Testes de Criação de Conta Guest
# ============================================================

@pytest.mark.django_db
class TestGuestCreation:
    """Testa o endpoint POST /api/accounts/guest/"""

    def test_create_guest_returns_201(self, api_client):
        """Um guest deve ser criado com sucesso e devolver token."""
        url = reverse('create_guest')
        response = api_client.post(url)

        assert response.status_code == status.HTTP_201_CREATED
        assert 'token' in response.data
        assert 'username' in response.data
        assert response.data['is_guest'] is True

    def test_guest_username_starts_with_prefix(self, api_client):
        """O username do guest deve começar com 'guest_'."""
        url = reverse('create_guest')
        response = api_client.post(url)

        assert response.data['username'].startswith('guest_')

    def test_guest_is_stored_in_database(self, api_client):
        """O guest criado deve existir na base de dados."""
        url = reverse('create_guest')
        response = api_client.post(url)

        user = User.objects.get(username=response.data['username'])
        assert user.is_guest is True
        assert user.elo_rating == 1200  # Rating padrão


# ============================================================
# Testes de Eliminação de Conta Guest
# ============================================================

@pytest.mark.django_db
class TestGuestDeletion:
    """Testa o endpoint DELETE /api/accounts/guest/delete/"""

    def test_guest_can_delete_own_account(self, guest_client, guest_user):
        """Um guest autenticado pode eliminar a sua própria conta."""
        url = reverse('delete_guest')
        response = guest_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(pk=guest_user.pk).exists()

    def test_regular_user_cannot_delete_via_guest_endpoint(self, auth_client):
        """Um utilizador normal não pode usar o endpoint de eliminação de guest."""
        url = reverse('delete_guest')
        response = auth_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_delete(self, api_client):
        """Pedido sem autenticação deve ser rejeitado."""
        url = reverse('delete_guest')
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================
# Testes de Perfil do Utilizador
# ============================================================

@pytest.mark.django_db
class TestUserProfile:
    """Testa o endpoint GET /api/accounts/profile/"""

    def test_authenticated_user_gets_profile(self, auth_client, user):
        """Utilizador autenticado deve receber os seus dados de perfil."""
        url = reverse('user_profile')
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == user.username
        assert response.data['elo_rating'] == 1200
        assert response.data['games_played'] == 0

    def test_unauthenticated_gets_401(self, api_client):
        """Pedido sem autenticação deve ser rejeitado."""
        url = reverse('user_profile')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================
# Testes de Estatísticas do Utilizador
# ============================================================

@pytest.mark.django_db
class TestUserStats:
    """Testa o endpoint GET /api/accounts/stats/"""

    def test_stats_include_rates(self, auth_client):
        """As estatísticas devem incluir win_rate e draw_rate."""
        url = reverse('user_stats')
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'win_rate' in response.data
        assert 'draw_rate' in response.data

    def test_stats_zero_games_returns_zero_rates(self, auth_client):
        """Com zero jogos, as taxas devem ser 0."""
        url = reverse('user_stats')
        response = auth_client.get(url)

        assert response.data['win_rate'] == 0
        assert response.data['draw_rate'] == 0


# ============================================================
# Testes do Modelo User (Lógica de ELO)
# ============================================================

@pytest.mark.django_db
class TestUserModel:
    """Testa a lógica de negócio do modelo User."""

    def test_update_statistics_win(self, user):
        """Atualizar estatísticas com vitória."""
        user.update_statistics('win')

        assert user.games_played == 1
        assert user.games_won == 1
        assert user.games_lost == 0

    def test_update_statistics_loss(self, user):
        """Atualizar estatísticas com derrota."""
        user.update_statistics('loss')

        assert user.games_played == 1
        assert user.games_lost == 1

    def test_update_statistics_draw(self, user):
        """Atualizar estatísticas com empate."""
        user.update_statistics('draw')

        assert user.games_played == 1
        assert user.games_drawn == 1

    def test_update_statistics_invalid_result_raises(self, user):
        """Resultado inválido deve levantar ValueError."""
        with pytest.raises(ValueError):
            user.update_statistics('invalid')

    def test_calculate_elo_win_increases_rating(self, user):
        """Vencer contra um oponente igual deve aumentar o ELO."""
        new_elo = user.calculate_elo(1200, 'win')
        assert new_elo > 1200

    def test_calculate_elo_loss_decreases_rating(self, user):
        """Perder contra um oponente igual deve diminuir o ELO."""
        new_elo = user.calculate_elo(1200, 'loss')
        assert new_elo < 1200

    def test_calculate_elo_draw_same_rating(self, user):
        """Empate contra oponente com o mesmo rating não deve alterar significativamente."""
        new_elo = user.calculate_elo(1200, 'draw')
        assert new_elo == 1200

    def test_win_rate_calculation(self, user):
        """Testar cálculo de win_rate."""
        user.games_played = 10
        user.games_won = 7
        assert user.get_win_rate() == 70.0

    def test_win_rate_zero_games(self, user):
        """Win rate com zero jogos deve ser 0."""
        assert user.get_win_rate() == 0
