"""
Testes para a app Tournaments.
Cobre: criação, adesão, saída, início, emparelhamentos, classificações, permissões.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from tournaments.models import (
    Tournament, TournamentParticipant, TournamentRound, TournamentPairing
)
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def tournament(db, user):
    """Torneio de teste criado pelo user principal."""
    t = Tournament.objects.create(
        name='Torneio Teste',
        description='Torneio para testes automatizados',
        tournament_type=Tournament.SWISS,
        status=Tournament.REGISTRATION,
        max_participants=16,
        created_by=user,
    )
    # Criador é participante automaticamente
    TournamentParticipant.objects.create(
        tournament=t, user=user, initial_rating=user.elo_rating
    )
    return t


# ============================================================
# Testes de Criação de Torneio
# ============================================================

@pytest.mark.django_db
class TestTournamentCreation:
    """Testa o endpoint POST /api/tournaments/"""

    def test_create_tournament(self, auth_client, user):
        """Utilizador autenticado pode criar um torneio."""
        url = reverse('tournament-list')
        response = auth_client.post(url, {
            'name': 'Novo Torneio',
            'tournament_type': 'SWISS',
            'max_participants': 8,
        }, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Novo Torneio'
        assert 'join_code' in response.data

    def test_guest_cannot_create_tournament(self, guest_client):
        """Utilizadores convidados não podem criar torneios."""
        url = reverse('tournament-list')
        response = guest_client.post(url, {
            'name': 'Torneio Guest',
            'tournament_type': 'SWISS',
        }, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_tournament_auto_adds_creator_as_participant(self, auth_client, user):
        """O criador deve ser adicionado automaticamente como participante."""
        url = reverse('tournament-list')
        response = auth_client.post(url, {
            'name': 'Torneio Auto',
            'tournament_type': 'SWISS',
            'max_participants': 8,
        }, format='json')

        tournament_id = response.data['id']
        assert TournamentParticipant.objects.filter(
            tournament_id=tournament_id, user=user
        ).exists()

    def test_unauthenticated_cannot_create(self, api_client):
        """Pedido sem autenticação deve ser rejeitado."""
        url = reverse('tournament-list')
        response = api_client.post(url, {
            'name': 'Torneio Anon',
        }, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================
# Testes de Adesão a Torneio
# ============================================================

@pytest.mark.django_db
class TestTournamentJoin:
    """Testa o endpoint POST /api/tournaments/{id}/join/"""

    def test_join_tournament(self, auth_client2, user2, tournament):
        """Utilizador pode aderir a um torneio em fase de registo."""
        url = reverse('tournament-join', args=[tournament.id])
        response = auth_client2.post(url)

        assert response.status_code == status.HTTP_201_CREATED
        assert TournamentParticipant.objects.filter(
            tournament=tournament, user=user2
        ).exists()

    def test_cannot_join_twice(self, auth_client, tournament):
        """O mesmo utilizador não pode aderir duas vezes."""
        url = reverse('tournament-join', args=[tournament.id])
        response = auth_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_guest_cannot_join(self, guest_client, tournament):
        """Utilizadores convidados não podem aderir a torneios."""
        url = reverse('tournament-join', args=[tournament.id])
        response = guest_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_join_full_tournament(self, auth_client2, user2, user, create_user):
        """Não é possível aderir a um torneio cheio."""
        t = Tournament.objects.create(
            name='Torneio Pequeno',
            tournament_type=Tournament.SWISS,
            max_participants=2,
            created_by=user,
        )
        TournamentParticipant.objects.create(
            tournament=t, user=user, initial_rating=1200
        )
        extra = create_user(username='filler')
        TournamentParticipant.objects.create(
            tournament=t, user=extra, initial_rating=1200
        )

        url = reverse('tournament-join', args=[t.id])
        response = auth_client2.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_join_started_tournament(self, auth_client2, tournament):
        """Não é possível aderir a um torneio que já começou."""
        tournament.status = Tournament.IN_PROGRESS
        tournament.save()

        url = reverse('tournament-join', args=[tournament.id])
        response = auth_client2.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================
# Testes de Saída do Torneio
# ============================================================

@pytest.mark.django_db
class TestTournamentLeave:
    """Testa o endpoint POST /api/tournaments/{id}/leave/"""

    def test_participant_can_leave(self, auth_client2, user2, tournament):
        """Participante pode sair durante a fase de registo."""
        TournamentParticipant.objects.create(
            tournament=tournament, user=user2, initial_rating=1300
        )

        url = reverse('tournament-leave', args=[tournament.id])
        response = auth_client2.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert not TournamentParticipant.objects.filter(
            tournament=tournament, user=user2
        ).exists()

    def test_organizer_cannot_leave(self, auth_client, tournament):
        """O organizador não pode sair do seu próprio torneio."""
        url = reverse('tournament-leave', args=[tournament.id])
        response = auth_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_leave_after_start(self, auth_client2, user2, tournament):
        """Não é possível sair após o torneio ter começado."""
        TournamentParticipant.objects.create(
            tournament=tournament, user=user2, initial_rating=1300
        )
        tournament.status = Tournament.IN_PROGRESS
        tournament.save()

        url = reverse('tournament-leave', args=[tournament.id])
        response = auth_client2.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================
# Testes de Início de Torneio
# ============================================================

@pytest.mark.django_db
class TestTournamentStart:
    """Testa o endpoint POST /api/tournaments/{id}/start/"""

    def test_only_organizer_can_start(self, auth_client2, tournament):
        """Apenas o organizador pode iniciar o torneio."""
        url = reverse('tournament-start', args=[tournament.id])
        response = auth_client2.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_start_with_less_than_2_participants(self, auth_client, user):
        """Torneio com menos de 2 participantes não pode ser iniciado."""
        t = Tournament.objects.create(
            name='Torneio Vazio',
            tournament_type=Tournament.SWISS,
            max_participants=8,
            created_by=user,
        )
        TournamentParticipant.objects.create(
            tournament=t, user=user, initial_rating=1200
        )

        url = reverse('tournament-start', args=[t.id])
        response = auth_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================
# Testes de Participantes
# ============================================================

@pytest.mark.django_db
class TestTournamentParticipants:
    """Testa o endpoint GET /api/tournaments/{id}/participants/"""

    def test_list_participants(self, auth_client, tournament, user):
        """Deve listar os participantes ativos do torneio."""
        url = reverse('tournament-participants', args=[tournament.id])
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1  # Apenas o criador


# ============================================================
# Testes de Classificações
# ============================================================

@pytest.mark.django_db
class TestTournamentStandings:
    """Testa o endpoint GET /api/tournaments/{id}/standings/"""

    def test_standings_returns_data(self, auth_client, tournament):
        """Classificações devem devolver dados dos participantes."""
        url = reverse('tournament-standings', args=[tournament.id])
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK


# ============================================================
# Testes de Adesão por Código
# ============================================================

@pytest.mark.django_db
class TestTournamentJoinByCode:
    """Testa o endpoint POST /api/join/"""

    def test_join_by_valid_code(self, auth_client2, tournament):
        """Utilizador pode aderir com um código válido."""
        url = reverse('tournament-join-list')
        response = auth_client2.post(url, {
            'join_code': tournament.join_code,
        }, format='json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_join_by_invalid_code(self, auth_client2):
        """Código inválido deve devolver 400."""
        url = reverse('tournament-join-list')
        response = auth_client2.post(url, {
            'join_code': 'INVALIDO',
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_guest_cannot_join_by_code(self, guest_client, tournament):
        """Convidados não podem aderir via código."""
        url = reverse('tournament-join-list')
        response = guest_client.post(url, {
            'join_code': tournament.join_code,
        }, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================
# Testes do Modelo Tournament
# ============================================================

@pytest.mark.django_db
class TestTournamentModel:
    """Testa a lógica de negócio do modelo Tournament."""

    def test_join_code_auto_generated(self, user):
        """O código de adesão deve ser gerado automaticamente."""
        t = Tournament.objects.create(
            name='Torneio Auto Code',
            tournament_type=Tournament.SWISS,
            created_by=user,
        )
        assert t.join_code is not None
        assert len(t.join_code) == 8

    def test_participant_count(self, tournament, user2):
        """Contar participantes ativos."""
        assert tournament.participant_count == 1

        TournamentParticipant.objects.create(
            tournament=tournament, user=user2, initial_rating=1300
        )
        assert tournament.participant_count == 2

    def test_is_full(self, tournament, create_user):
        """Verificar se o torneio está cheio."""
        tournament.max_participants = 2
        tournament.save()

        extra = create_user(username='extra')
        TournamentParticipant.objects.create(
            tournament=tournament, user=extra, initial_rating=1200
        )

        assert tournament.is_full is True

    def test_participant_score_update(self, tournament, user):
        """Atualizar pontuação do participante."""
        participant = TournamentParticipant.objects.get(
            tournament=tournament, user=user
        )

        participant.update_score('win')
        assert participant.score == 1.0

        participant.update_score('draw')
        assert participant.score == 1.5

        participant.update_score('loss')
        assert participant.score == 1.5  # Derrota não adiciona pontos
