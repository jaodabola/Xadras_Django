"""
Testes para a app Game.
Cobre: criação de jogos, entrada em jogos, jogadas, fim de jogo, replay, listagem.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from game.models import Game, Move
from django.contrib.auth import get_user_model

User = get_user_model()

INITIAL_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'


# ============================================================
# Testes de Criação de Jogo
# ============================================================

@pytest.mark.django_db
class TestGameCreation:
    """Testa o endpoint POST /api/game/"""

    def test_create_game(self, auth_client, user):
        """Criar um jogo deve devolver status PENDING."""
        url = reverse('game-list')
        response = auth_client.post(url, {}, format='json')

        if response.status_code != status.HTTP_201_CREATED:
            print(f"Validation Error: {response.data}")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'PENDING'
        assert response.data['white_player']['username'] == user.username

    def test_create_game_unauthenticated(self, api_client):
        """Utilizador não autenticado não pode criar jogos."""
        url = reverse('game-list')
        response = api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_game_has_initial_fen(self, auth_client):
        """O jogo criado deve ter o FEN inicial padrão."""
        url = reverse('game-list')
        response = auth_client.post(url, {}, format='json')

        assert response.data['fen_string'] == INITIAL_FEN


# ============================================================
# Testes de Entrada em Jogo
# ============================================================

@pytest.mark.django_db
class TestGameJoin:
    """Testa o endpoint POST /api/game/{id}/join/"""

    def test_join_pending_game(self, auth_client, auth_client2, user, user2):
        """O segundo jogador pode entrar num jogo PENDING."""
        # Criar jogo com user1
        create_url = reverse('game-list')
        create_resp = auth_client.post(create_url, {}, format='json')
        game_id = create_resp.data['id']

        # User2 entra no jogo
        join_url = reverse('game-join', args=[game_id])
        response = auth_client2.post(join_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'IN_PROGRESS'
        assert response.data['black_player']['username'] == user2.username

    def test_cannot_join_in_progress_game(self, auth_client, auth_client2, user, user2, create_user):
        """Não é possível entrar num jogo que já está em curso."""
        # Criar e iniciar jogo
        create_url = reverse('game-list')
        create_resp = auth_client.post(create_url, {}, format='json')
        game_id = create_resp.data['id']

        join_url = reverse('game-join', args=[game_id])
        auth_client2.post(join_url)  # user2 entra

        # Terceiro utilizador tenta entrar
        user3 = create_user(username='testuser3')
        from rest_framework.test import APIClient
        from rest_framework.authtoken.models import Token
        client3 = APIClient()
        token3, _ = Token.objects.get_or_create(user=user3)
        client3.credentials(HTTP_AUTHORIZATION=f'Token {token3.key}')

        response = client3.post(join_url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================
# Testes de Fim de Jogo
# ============================================================

@pytest.mark.django_db
class TestGameEnd:
    """Testa o endpoint POST /api/game/{id}/end/"""

    @pytest.fixture
    def active_game(self, user, user2):
        """Cria um jogo em curso entre dois jogadores."""
        game = Game.objects.create(
            white_player=user,
            black_player=user2,
            status='IN_PROGRESS'
        )
        return game

    def test_end_game_white_wins(self, auth_client, active_game, user, user2):
        """Terminar jogo com vitória das brancas."""
        url = reverse('game-end', args=[active_game.id])
        response = auth_client.post(url, {'result': 'WHITE_WIN'}, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['result'] == 'WHITE_WIN'
        assert response.data['status'] == 'FINISHED'

        # Verificar que as estatísticas foram atualizadas
        user.refresh_from_db()
        user2.refresh_from_db()
        assert user.games_won == 1
        assert user2.games_lost == 1

    def test_end_game_updates_elo(self, auth_client, active_game, user, user2):
        """O ELO dos jogadores deve ser atualizado após o fim do jogo."""
        old_white_elo = user.elo_rating
        old_black_elo = user2.elo_rating

        url = reverse('game-end', args=[active_game.id])
        auth_client.post(url, {'result': 'WHITE_WIN'}, format='json')

        user.refresh_from_db()
        user2.refresh_from_db()
        assert user.elo_rating > old_white_elo
        assert user2.elo_rating < old_black_elo

    def test_end_game_invalid_result(self, auth_client, active_game):
        """Resultado inválido deve devolver 400."""
        url = reverse('game-end', args=[active_game.id])
        response = auth_client.post(url, {'result': 'INVALID'}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_end_pending_game(self, auth_client, user):
        """Não é possível terminar um jogo que não está em curso."""
        game = Game.objects.create(white_player=user, status='PENDING')
        url = reverse('game-end', args=[game.id])
        response = auth_client.post(url, {'result': 'DRAW'}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================
# Testes de Listagem de Jogos
# ============================================================

@pytest.mark.django_db
class TestGameList:
    """Testa o endpoint GET /api/game/my_games/"""

    def test_my_games_returns_user_games(self, auth_client, user, user2):
        """Deve listar apenas jogos do utilizador autenticado."""
        Game.objects.create(white_player=user, black_player=user2, status='FINISHED')
        Game.objects.create(white_player=user2, black_player=user, status='FINISHED')

        url = reverse('game-my-games')
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_my_games_empty_for_new_user(self, auth_client):
        """Utilizador novo não deve ter jogos."""
        url = reverse('game-my-games')
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0


# ============================================================
# Testes de Replay
# ============================================================

@pytest.mark.django_db
class TestGameReplay:
    """Testa o endpoint GET /api/game/{id}/replay/"""

    def test_replay_returns_fens(self, auth_client, user, user2):
        """Replay deve devolver a lista de FENs."""
        game = Game.objects.create(
            white_player=user, black_player=user2, status='FINISHED'
        )
        Move.objects.create(
            game=game, move_number=1, move_san='e4',
            fen_after='rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1'
        )

        url = reverse('game-replay', args=[game.id])
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['fens']) == 2  # FEN inicial + 1 jogada
        assert response.data['total_moves'] == 1
