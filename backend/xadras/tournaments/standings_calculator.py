# XADRAS - Calculadora de Classificação de Torneios
# Implementação pela Tournament Logic AI
# Prioridade: CRÍTICA - Desempates (Buchholz, Sonneborn-Berger, Confronto Direto)

from django.db import models
from django.contrib.auth import get_user_model
from .models import Tournament, TournamentParticipant, TournamentPairing
from typing import List, Dict, Tuple
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class TournamentStandingsCalculator:
    """
    Calcular a classificação do torneio com um sistema abrangente de desempates

    Critérios implementados:
    1. Buchholz Score (soma das pontuações dos adversários)
    2. Sonneborn-Berger Score (soma das pontuações dos adversários derrotados + metade dos adversários com quem empatou)
    3. Confronto Direto (resultados cabeça-a-cabeça entre tied players)
    4. Número de vitórias
    5. Rating inicial (mais alto vence o empate)
    """

    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self.participants = list(
            tournament.participants.filter(is_active=True)
        )
        self.pairings = list(
            TournamentPairing.objects.filter(
                round__tournament=tournament,
                result__isnull=False
            ).select_related('white_player', 'black_player', 'bye_player')
        )

        # Cache para performance
        self._opponent_cache = {}
        self._result_cache = {}

    def calculate_standings(self) -> List[Dict]:
        """
        Calcular a classificação completa do torneio com todos os desempates

        Retorna:
            Lista da classificação dos participantes ordenada por posição
        """
        logger.info(
            f"Calculando classificação para o torneio {self.tournament.name}")

        standings = []

        for participant in self.participants:
            standing = self._calculate_participant_standing(participant)
            standings.append(standing)

        # Ordenar por todos os critérios de desempate
        standings.sort(key=lambda x: (
            -x['score'],                    # Primário: pontuação mais alta
            -x['buchholz_score'],          # 1º desempate: Buchholz
            -x['sonneborn_berger_score'],  # 2º desempate: Sonneborn-Berger
            -x['direct_encounter_score'],   # 3º desempate: Confronto direto
            -x['wins'],                     # 4º desempate: Mais vitórias
            # 5º desempate: Rating inicial mais alto
            -x['initial_rating']
        ))

        # Atribuir posições
        for i, standing in enumerate(standings, 1):
            standing['position'] = i

        # Atualizar pontuações de desempate dos participantes na base de dados
        self._update_tiebreak_scores(standings)

        logger.info(f"Classificação calculada para {len(standings)} participantes")
        return standings

    def _calculate_participant_standing(self, participant: TournamentParticipant) -> Dict:
        """Calcular a informação completa da classificação para um participante"""
        user = participant.user

        # Obter estatísticas básicas de jogo
        games_played, wins, draws, losses = self._get_game_statistics(user)

        # Calcular pontuações de desempate
        buchholz_score = self._calculate_buchholz_score(user)
        sonneborn_berger_score = self._calculate_sonneborn_berger_score(user)
        direct_encounter_score = self._calculate_direct_encounter_score(user)

        return {
            'participant_id': participant.id,
            'player_id': str(user.id),
            'player_name': user.username,
            'score': participant.score,
            'games_played': games_played,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'buchholz_score': buchholz_score,
            'sonneborn_berger_score': sonneborn_berger_score,
            'direct_encounter_score': direct_encounter_score,
            'initial_rating': participant.initial_rating,
            'seed': participant.seed,
            'position': 0  # Será definido após a ordenação
        }

    def _get_game_statistics(self, user: User) -> Tuple[int, int, int, int]:
        """
        Obter estatísticas básicas de jogo para um utilizador

        Retorna:
            Tuplo de (jogos_jogados, vitórias, empates, derrotas)
        """
        if user.id in self._result_cache:
            return self._result_cache[user.id]

        wins = draws = losses = 0

        for pairing in self.pairings:
            if pairing.bye_player == user:
                # Bye conta como uma vitória
                wins += 1
            elif pairing.white_player == user:
                if pairing.result == TournamentPairing.WHITE_WIN:
                    wins += 1
                elif pairing.result == TournamentPairing.DRAW:
                    draws += 1
                elif pairing.result in [TournamentPairing.BLACK_WIN, TournamentPairing.FORFEIT_WHITE]:
                    losses += 1
            elif pairing.black_player == user:
                if pairing.result == TournamentPairing.BLACK_WIN:
                    wins += 1
                elif pairing.result == TournamentPairing.DRAW:
                    draws += 1
                elif pairing.result in [TournamentPairing.WHITE_WIN, TournamentPairing.FORFEIT_BLACK]:
                    losses += 1

        games_played = wins + draws + losses
        result = (games_played, wins, draws, losses)
        self._result_cache[user.id] = result

        return result

    def _calculate_buchholz_score(self, user: User) -> float:
        """
        Calcular a pontuação Buchholz (soma das pontuações dos adversários)

        A pontuação Buchholz é a soma das pontuações de todos os adversários
        que um jogador enfrentou no torneio.
        """
        opponents = self._get_opponents(user)
        buchholz_score = 0.0

        for opponent in opponents:
            try:
                opponent_participant = TournamentParticipant.objects.get(
                    tournament=self.tournament,
                    user=opponent,
                    is_active=True
                )
                buchholz_score += opponent_participant.score
            except TournamentParticipant.DoesNotExist:
                # Adversário não encontrado (não deve acontecer), saltar
                continue

        return buchholz_score

    def _calculate_sonneborn_berger_score(self, user: User) -> float:
        """
        Calcular a pontuação Sonneborn-Berger

        A pontuação Sonneborn-Berger é a soma de:
        - Pontuações totais de adversários derrotados
        - Metade das pontuações de adversários com quem empatou
        - Zero para adversários que derrotaram este jogador
        """
        sonneborn_berger_score = 0.0

        for pairing in self.pairings:
            opponent = None
            result_for_user = None

            if pairing.bye_player == user:
                # O bye não contribui para o Sonneborn-Berger
                continue
            elif pairing.white_player == user:
                opponent = pairing.black_player
                if pairing.result == TournamentPairing.WHITE_WIN:
                    result_for_user = 'win'
                elif pairing.result == TournamentPairing.DRAW:
                    result_for_user = 'draw'
                else:
                    result_for_user = 'loss'
            elif pairing.black_player == user:
                opponent = pairing.white_player
                if pairing.result == TournamentPairing.BLACK_WIN:
                    result_for_user = 'win'
                elif pairing.result == TournamentPairing.DRAW:
                    result_for_user = 'draw'
                else:
                    result_for_user = 'loss'

            if opponent and result_for_user:
                try:
                    opponent_participant = TournamentParticipant.objects.get(
                        tournament=self.tournament,
                        user=opponent,
                        is_active=True
                    )

                    if result_for_user == 'win':
                        # Adicionar pontuação total do adversário derrotado
                        sonneborn_berger_score += opponent_participant.score
                    elif result_for_user == 'draw':
                        # Adicionar metade da pontuação do adversário com quem empatou
                        sonneborn_berger_score += opponent_participant.score * 0.5
                    # Para derrotas, não adiciona nada

                except TournamentParticipant.DoesNotExist:
                    continue

        return sonneborn_berger_score

    def _calculate_direct_encounter_score(self, user: User) -> float:
        """
        Calcular a pontuação de confronto direto

        Isto é usado ao comparar jogadores com a mesma pontuação.
        Retorna a pontuação alcançada em jogos diretamente entre jogadores empatados.

        Nota: Esta é uma versão simplificada. A implementação completa exigiria 
        saber quais os jogadores específicos que estão empatados.
        """
        # Por agora, retorna 0. Isto seria calculado ao resolver
        # empates entre jogadores específicos
        return 0.0

    def _get_opponents(self, user: User) -> List[User]:
        """Obter lista de todos os adversários que um utilizador enfrentou"""
        if user.id in self._opponent_cache:
            return self._opponent_cache[user.id]

        opponents = []

        for pairing in self.pairings:
            if pairing.bye_player == user:
                # O bye não tem adversário
                continue
            elif pairing.white_player == user and pairing.black_player:
                opponents.append(pairing.black_player)
            elif pairing.black_player == user and pairing.white_player:
                opponents.append(pairing.white_player)

        self._opponent_cache[user.id] = opponents
        return opponents

    def _update_tiebreak_scores(self, standings: List[Dict]):
        """Atualizar as pontuações de desempate na base de dados"""
        for standing in standings:
            try:
                participant = TournamentParticipant.objects.get(
                    id=standing['participant_id']
                )

                participant.tiebreak_scores = {
                    'buchholz': standing['buchholz_score'],
                    'sonneborn_berger': standing['sonneborn_berger_score'],
                    'direct_encounter': standing['direct_encounter_score']
                }
                participant.save(update_fields=['tiebreak_scores'])

            except TournamentParticipant.DoesNotExist:
                logger.warning(
                    f"Participante {standing['participant_id']} não encontrado para atualização de desempate")

    def calculate_direct_encounter_between_players(self, players: List[User]) -> Dict[int, float]:
        """
        Calcular as pontuações de confronto direto entre jogadores específicos empatados

        Args:
            players: Lista de jogadores empatados para comparar

        Returns:
            Dicionário mapeando user_id para a pontuação de confronto direto
        """
        player_ids = {player.id for player in players}
        direct_scores = {player.id: 0.0 for player in players}

        # Encontrar todos os emparelhamentos entre estes jogadores específicos
        for pairing in self.pairings:
            if (pairing.white_player and pairing.black_player and
                pairing.white_player.id in player_ids and
                    pairing.black_player.id in player_ids):

                if pairing.result == TournamentPairing.WHITE_WIN:
                    direct_scores[pairing.white_player.id] += 1.0
                elif pairing.result == TournamentPairing.BLACK_WIN:
                    direct_scores[pairing.black_player.id] += 1.0
                elif pairing.result == TournamentPairing.DRAW:
                    direct_scores[pairing.white_player.id] += 0.5
                    direct_scores[pairing.black_player.id] += 0.5

        return direct_scores


def calculate_tournament_standings(tournament_id: str) -> List[Dict]:
    """
    Função principal para calcular a classificação do torneio

    Args:
        tournament_id: UUID do torneio

    Returns:
        Lista de dicionários de classificação ordenada por posição
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        calculator = TournamentStandingsCalculator(tournament)
        return calculator.calculate_standings()

    except Tournament.DoesNotExist:
        raise ValueError(f"Torneio com ID {tournament_id} não encontrado")


def update_participant_tiebreakers(tournament_id: str):
    """
    Atualizar as pontuações de desempate para todos os participantes num torneio

    Args:
        tournament_id: UUID do torneio
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        calculator = TournamentStandingsCalculator(tournament)

        # Calcular classificação (isto também atualiza os desempates)
        calculator.calculate_standings()

        logger.info(
            f"Atualizadas pontuações de desempate para o torneio {tournament.name}")

    except Tournament.DoesNotExist:
        raise ValueError(f"Torneio com ID {tournament_id} não encontrado")
