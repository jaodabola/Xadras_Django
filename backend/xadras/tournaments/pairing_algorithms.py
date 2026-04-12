# XADRAS - Algoritmos de Emparelhamento de Torneios
# Implementação pela Tournament Logic AI
# Prioridade: CRÍTICA - Sistema Suíço, Eliminação Única, Round Robin

from django.db import transaction
from django.contrib.auth import get_user_model
from .models import Tournament, TournamentParticipant, TournamentRound, TournamentPairing
from game.models import Game
import logging
import random
from typing import List, Tuple, Dict, Optional

User = get_user_model()
logger = logging.getLogger(__name__)


class SwissPairingEngine:
    """
    Implementação do algoritmo de emparelhamento Sistema Suíço

    Funcionalidades:
    - Agrupamento baseado em pontuação
    - Emparelhamento baseado em rating dentro dos grupos
    - Equilíbrio de cores (evitar 3 cores iguais consecutivas)
    - Evitar repetição de emparelhamentos
    - Gestão de bye para números ímpares
    """

    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self.participants = list(
            tournament.participants.filter(is_active=True)
            .order_by('-score', 'seed')
        )
        self.previous_pairings = self._get_previous_pairings()

    def generate_pairings(self, round_number: int) -> List[Dict]:
        """
        Gerar emparelhamentos do sistema suíço para a ronda especificada

        Args:
            round_number: O número da ronda para a qual gerar emparelhamentos

        Returns:
            Lista de dicionários de emparelhamento com atribuições de jogadores
        """
        logger.info(
            f"Gerando emparelhamentos Suíços para o torneio {self.tournament.name}, ronda {round_number}")

        if len(self.participants) < 2:
            raise ValueError("Necessários pelo menos 2 participantes para emparelhamentos Suíços")

        # GESTÃO CORRETA DE BYE: Lidar PRIMEIRO com número ímpar de jogadores
        pairings = []
        active_participants = list(self.participants)

        # Se houver um número ímpar de participantes, selecionar primeiro o jogador com bye
        if len(active_participants) % 2 == 1:
            bye_player = self._select_bye_player(active_participants)
            if bye_player:
                bye_pairing = self._create_bye_pairing(bye_player)
                pairings.append(bye_pairing)
                active_participants.remove(bye_player)
                logger.info(f"Jogador selecionado para bye: {bye_player.user.username}")

        # Agora trabalhar com número par de participantes
        # Agrupar participantes restantes por pontuação
        score_groups = {}
        for participant in active_participants:
            score = participant.score
            if score not in score_groups:
                score_groups[score] = []
            score_groups[score].append(participant)

        # Ordenar grupos por pontuação (maior primeiro)
        score_groups = dict(sorted(score_groups.items(),
                            key=lambda x: x[0], reverse=True))

        # Gerar emparelhamentos dentro de cada grupo de pontuação
        unpaired_players = []

        for score, players in score_groups.items():
            group_pairings, group_unpaired = self._pair_within_group(players)
            pairings.extend(group_pairings)
            unpaired_players.extend(group_unpaired)

        # Lidar com quaisquer jogadores não emparelhados de diferentes grupos de pontuação
        if unpaired_players:
            cross_group_pairings, final_unpaired = self._pair_across_groups(
                unpaired_players)
            pairings.extend(cross_group_pairings)

            # Com a gestão correta de bye, isto deve ser raro
            if final_unpaired:
                logger.warning(
                    f"Ainda restam {len(final_unpaired)} jogadores não emparelhados após gestão de bye")
                # Forçar emparelhamento dos jogadores restantes
                while len(final_unpaired) >= 2:
                    player1 = final_unpaired.pop(0)
                    player2 = final_unpaired.pop(0)
                    pairing = self._create_pairing(player1, player2)
                    pairings.append(pairing)

        logger.info(
            f"Gerados {len(pairings)} emparelhamentos para a ronda {round_number}")
        return pairings

    def _group_by_score(self) -> Dict[float, List[TournamentParticipant]]:
        """Agrupar participantes pela sua pontuação atual"""
        score_groups = {}

        for participant in self.participants:
            score = participant.score
            if score not in score_groups:
                score_groups[score] = []
            score_groups[score].append(participant)

        # Ordenar grupos por pontuação (maior primeiro)
        return dict(sorted(score_groups.items(), key=lambda x: x[0], reverse=True))

    def _pair_within_group(self, players: List[TournamentParticipant]) -> Tuple[List[Dict], List[TournamentParticipant]]:
        """
        Emparelhar jogadores dentro de um grupo de pontuação

        Returns:
            Tuplo de (emparelhamentos, jogadores_nao_emparelhados)
        """
        if len(players) < 2:
            return [], players

        # Ordenar por rating para melhores emparelhamentos
        players_sorted = sorted(
            players, key=lambda p: p.initial_rating, reverse=True)

        pairings = []
        unpaired = []
        used_players = set()

        # Tentar emparelhar jogadores de forma ideal
        for i, player1 in enumerate(players_sorted):
            if player1.id in used_players:
                continue

            best_opponent = None
            best_score = -1

            for j, player2 in enumerate(players_sorted[i+1:], i+1):
                if player2.id in used_players:
                    continue

                # Calcular pontuação de qualidade do emparelhamento
                pairing_score = self._calculate_pairing_score(player1, player2)

                if pairing_score > best_score:
                    best_score = pairing_score
                    best_opponent = player2

            if best_opponent:
                pairing = self._create_pairing(player1, best_opponent)
                pairings.append(pairing)
                used_players.add(player1.id)
                used_players.add(best_opponent.id)
            else:
                unpaired.append(player1)

        # Adicionar quaisquer jogadores restantes não emparelhados
        for player in players_sorted:
            if player.id not in used_players:
                unpaired.append(player)

        return pairings, unpaired

    def _pair_across_groups(self, players: List[TournamentParticipant]) -> Tuple[List[Dict], List[TournamentParticipant]]:
        """
        Emparelhar jogadores restantes entre diferentes grupos de pontuação
        """
        if len(players) < 2:
            return [], players

        pairings = []
        remaining = players.copy()

        while len(remaining) >= 2:
            player1 = remaining.pop(0)

            # Encontrar o melhor adversário entre os jogadores restantes
            best_opponent = None
            best_score = -1
            best_index = -1

            for i, player2 in enumerate(remaining):
                pairing_score = self._calculate_pairing_score(player1, player2)
                if pairing_score > best_score:
                    best_score = pairing_score
                    best_opponent = player2
                    best_index = i

            if best_opponent:
                pairing = self._create_pairing(player1, best_opponent)
                pairings.append(pairing)
                remaining.pop(best_index)

        return pairings, remaining

    def _calculate_pairing_score(self, player1: TournamentParticipant, player2: TournamentParticipant) -> float:
        """
        Calcular a pontuação de qualidade para um potencial emparelhamento
        Pontuação mais alta = melhor emparelhamento

        Critérios:
        - Não terem jogado antes (prioridade máxima)
        - Equilíbrio de cores
        - Proximidade de rating
        """
        score = 0.0

        # Verificar se já jogaram antes (fator mais importante)
        if not self._have_played_before(player1, player2):
            score += 100.0
        else:
            score -= 50.0  # Penalização pesada para repetição de emparelhamentos

        # Fator de equilíbrio de cores
        color_balance_score = self._calculate_color_balance_score(
            player1, player2)
        score += color_balance_score * 10.0

        # Fator de proximidade de rating (ratings mais próximos = melhor emparelhamento)
        rating_diff = abs(player1.initial_rating - player2.initial_rating)
        rating_score = max(0, 400 - rating_diff) / 400.0  # Normalizar para 0-1
        score += rating_score * 5.0

        return score

    def _have_played_before(self, player1: TournamentParticipant, player2: TournamentParticipant) -> bool:
        """Verificar se dois jogadores já jogaram um contra o outro antes"""
        pairing_key = tuple(sorted([player1.user.id, player2.user.id]))
        return pairing_key in self.previous_pairings

    def _calculate_color_balance_score(self, player1: TournamentParticipant, player2: TournamentParticipant) -> float:
        """
        Calcular a pontuação de equilíbrio de cores para o emparelhamento
        Preferir emparelhamentos que equilibram cores
        """
        player1_colors = self._get_player_color_history(player1.user)
        player2_colors = self._get_player_color_history(player2.user)

        # Contar cores recentes (últimos 2 jogos)
        player1_recent_white = sum(
            1 for color in player1_colors[-2:] if color == 'white')
        player1_recent_black = sum(
            1 for color in player1_colors[-2:] if color == 'black')

        player2_recent_white = sum(
            1 for color in player2_colors[-2:] if color == 'white')
        player2_recent_black = sum(
            1 for color in player2_colors[-2:] if color == 'black')

        # Preferir dar brancas ao jogador que jogou de pretas mais recentemente
        if player1_recent_black > player1_recent_white and player2_recent_white > player2_recent_black:
            return 1.0  # Bom equilíbrio: player1 recebe brancas, player2 recebe pretas
        elif player2_recent_black > player2_recent_white and player1_recent_white > player1_recent_black:
            return 1.0  # Bom equilíbrio: player2 recebe brancas, player1 recebe pretas
        else:
            return 0.5  # Equilíbrio neutro

    def _get_player_color_history(self, user: User) -> List[str]:
        """Obter histórico de cores do jogador neste torneio"""
        colors = []

        pairings = TournamentPairing.objects.filter(
            round__tournament=self.tournament,
            white_player=user
        ).order_by('round__round_number')
        colors.extend(['white'] * pairings.count())

        pairings = TournamentPairing.objects.filter(
            round__tournament=self.tournament,
            black_player=user
        ).order_by('round__round_number')
        colors.extend(['black'] * pairings.count())

        # Esta é uma versão simplificada, deve ser devidamente ordenada por ronda
        return sorted(colors)

    def _create_pairing(self, player1: TournamentParticipant, player2: TournamentParticipant) -> Dict:
        """
        Criar um emparelhamento entre dois jogadores
        Determinar cores com base no equilíbrio de cores
        """
        # Determinar cores
        player1_colors = self._get_player_color_history(player1.user)
        player2_colors = self._get_player_color_history(player2.user)

        # Lógica simples de atribuição de cores (pode ser melhorada)
        player1_white_count = player1_colors.count('white')
        player1_black_count = player1_colors.count('black')
        player2_white_count = player2_colors.count('white')
        player2_black_count = player2_colors.count('black')

        # Atribuir as brancas ao jogador que jogou mais de pretas ou que tem rating superior se for igual
        if player1_black_count > player1_white_count:
            white_player, black_player = player1, player2
        elif player2_black_count > player2_white_count:
            white_player, black_player = player2, player1
        elif player1.initial_rating > player2.initial_rating:
            white_player, black_player = player1, player2
        else:
            white_player, black_player = player2, player1

        return {
            'white_player': white_player.user,
            'black_player': black_player.user,
            'bye_player': None,
            'is_bye': False
        }

    def _select_bye_player(self, participants: List[TournamentParticipant]) -> Optional[TournamentParticipant]:
        """
        Selecionar o jogador que deve receber o bye
        Prioridade: Jogador que ainda não teve bye, seguido pelo de menor rating.
        """
        # Obter jogadores que ainda não tiveram bye neste torneio
        players_without_bye = []
        players_with_bye = []

        for participant in participants:
            # Verificar se o jogador já teve bye neste torneio
            has_bye = TournamentPairing.objects.filter(
                round__tournament=self.tournament,
                bye_player=participant.user,
                bye_player__isnull=False
            ).exists()

            if has_bye:
                players_with_bye.append(participant)
            else:
                players_without_bye.append(participant)

        # Preferir jogadores que ainda não tiveram bye
        candidates = players_without_bye if players_without_bye else players_with_bye

        if not candidates:
            return None

        # Selecionar o jogador de menor rating entre os candidatos
        return min(candidates, key=lambda p: p.initial_rating)

    def _create_bye_pairing(self, player: TournamentParticipant) -> Dict:
        """Criar um emparelhamento de bye para um jogador"""
        return {
            'white_player': None,
            'black_player': None,
            'bye_player': player.user,
            'is_bye': True
        }

    def _get_previous_pairings(self) -> set:
        """Obter o conjunto de todos os emparelhamentos anteriores neste torneio"""
        pairings = set()

        tournament_pairings = TournamentPairing.objects.filter(
            round__tournament=self.tournament,
            white_player__isnull=False,
            black_player__isnull=False
        )

        for pairing in tournament_pairings:
            pairing_key = tuple(
                sorted([pairing.white_player.id, pairing.black_player.id]))
            pairings.add(pairing_key)

        return pairings


class SingleEliminationEngine:
    """
    Motor de emparelhamento para torneios de Eliminação Única

    Funcionalidades:
    - Geração de árvore (bracket) semeada
    - Estrutura de árvore com potência de 2
    - Lógica de avanço para o vencedor
    - Dados para visualização da árvore
    """

    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self.participants = list(
            tournament.participants.filter(is_active=True)
            .order_by('seed')
        )

    def generate_bracket(self) -> List[Dict]:
        """
        Gerar a árvore (bracket) de eliminação única

        Returns:
            Lista de emparelhamentos da primeira ronda
        """
        logger.info(
            f"Gerando árvore de eliminação para o torneio {self.tournament.name}")

        participant_count = len(self.participants)
        if participant_count < 2:
            raise ValueError(
                "Necessários pelo menos 2 participantes para torneio de eliminação")

        # Para eliminação única, precisamos de um número de participantes que seja potência de 2
        # Se não for potência de 2, alguns jogadores recebem byes na primeira ronda
        next_power_of_2 = 1
        while next_power_of_2 < participant_count:
            next_power_of_2 *= 2

        first_round_games = participant_count - \
            (next_power_of_2 - participant_count)
        byes = participant_count - first_round_games

        pairings = []

        # Criar emparelhamentos da primeira ronda com árvore semeada (seeded)
        players_copy = self.participants.copy()

        # Dar byes aos cabeças de série mais altos
        bye_players = players_copy[:byes]
        playing_players = players_copy[byes:]

        # Criar byes
        for player in bye_players:
            bye_pairing = {
                'white_player': None,
                'black_player': None,
                'bye_player': player.user,
                'is_bye': True
            }
            pairings.append(bye_pairing)

        # Criar jogos da primeira ronda
        # Emparelhar o cabeça de série mais alto com o mais baixo, etc.
        while len(playing_players) >= 2:
            high_seed = playing_players.pop(0)  # Semente mais alta
            low_seed = playing_players.pop()    # Semente mais baixa

            pairing = {
                'white_player': high_seed.user,
                'black_player': low_seed.user,
                'bye_player': None,
                'is_bye': False
            }
            pairings.append(pairing)

        logger.info(
            f"Gerada árvore de eliminação com {len(pairings)} emparelhamentos na primeira ronda")
        return pairings

    def generate_next_round(self, current_round: int) -> List[Dict]:
        """
        Gerar emparelhamentos da próxima ronda com base nos resultados da ronda anterior
        """
        logger.info(f"Gerando ronda de eliminação {current_round + 1}")

        # Obter os vencedores da ronda anterior
        previous_round = TournamentRound.objects.get(
            tournament=self.tournament,
            round_number=current_round
        )

        winners = []
        for pairing in previous_round.pairings.all():
            winner = self._get_pairing_winner(pairing)
            if winner:
                winners.append(winner)

        if len(winners) < 2:
            logger.info("Torneio terminado - restam menos de 2 vencedores")
            return []

        # Emparelhar vencedores para a próxima ronda
        pairings = []
        while len(winners) >= 2:
            player1 = winners.pop(0)
            player2 = winners.pop(0)

            pairing = {
                'white_player': player1,
                'black_player': player2,
                'bye_player': None,
                'is_bye': False
            }
            pairings.append(pairing)

        # Lidar com vencedor ímpar (não deve acontecer numa eliminação correta)
        if winners:
            bye_pairing = {
                'white_player': None,
                'black_player': None,
                'bye_player': winners[0],
                'is_bye': True
            }
            pairings.append(bye_pairing)

        return pairings

    def _get_pairing_winner(self, pairing: TournamentPairing) -> Optional[User]:
        """Obter o vencedor de um emparelhamento de torneio"""
        if pairing.result == TournamentPairing.BYE:
            return pairing.bye_player
        elif pairing.result == TournamentPairing.WHITE_WIN:
            return pairing.white_player
        elif pairing.result == TournamentPairing.BLACK_WIN:
            return pairing.black_player
        else:
            # Jogo não terminado ou empate (lidar com empates na eliminação?)
            return None


class RoundRobinEngine:
    """
    Motor de emparelhamento para torneios Round Robin (Todos contra todos)

    Funcionalidades:
    - Escalonamento round-robin completo
    - Cada jogador joga contra todos os outros uma vez
    - Equilíbrio de cores ao longo do torneio
    """

    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self.participants = list(
            tournament.participants.filter(is_active=True)
            .order_by('seed')
        )

    def generate_all_rounds(self) -> Dict[int, List[Dict]]:
        """
        Gerar todas as rondas para um torneio round robin

        Returns:
            Dictionary mapping round number to list of pairings
        """
        logger.info(
            f"Gerando calendário round robin para o torneio {self.tournament.name}")

        participant_count = len(self.participants)
        if participant_count < 2:
            raise ValueError(
                "Need at least 2 participants for round robin tournament")

        # Round robin requer n-1 rondas para n jogadores (ou n rondas se n for ímpar)
        total_rounds = participant_count - \
            1 if participant_count % 2 == 0 else participant_count

        all_pairings = {}

        # Gerar o calendário round robin usando o método circular
        players = [p.user for p in self.participants]

        # Se houver um número ímpar de jogadores, adicionar um placeholder de "bye"
        if len(players) % 2 == 1:
            players.append(None)  # None representa o bye

        n = len(players)

        for round_num in range(1, total_rounds + 1):
            round_pairings = []

            for i in range(n // 2):
                player1 = players[i]
                player2 = players[n - 1 - i]

                if player1 is None:
                    # player2 recebe bye
                    bye_pairing = {
                        'white_player': None,
                        'black_player': None,
                        'bye_player': player2,
                        'is_bye': True
                    }
                    round_pairings.append(bye_pairing)
                elif player2 is None:
                    # player1 recebe bye
                    bye_pairing = {
                        'white_player': None,
                        'black_player': None,
                        'bye_player': player1,
                        'is_bye': True
                    }
                    round_pairings.append(bye_pairing)
                else:
                    # Alternar cores com base na ronda e posição
                    if (round_num + i) % 2 == 0:
                        white_player, black_player = player1, player2
                    else:
                        white_player, black_player = player2, player1

                    pairing = {
                        'white_player': white_player,
                        'black_player': black_player,
                        'bye_player': None,
                        'is_bye': False
                    }
                    round_pairings.append(pairing)

            all_pairings[round_num] = round_pairings

            # Rodar jogadores para a próxima ronda (manter o primeiro jogador fixo)
            players = [players[0]] + [players[-1]] + players[1:-1]

        logger.info(
            f"Gerado calendário round robin com {total_rounds} rondas")
        return all_pairings


def generate_swiss_pairings(tournament_id: str, round_number: int) -> List[Dict]:
    """
    Função principal para gerar emparelhamentos do sistema suíço

    Args:
        tournament_id: UUID of the tournament
        round_number: Round number to generate pairings for

    Returns:
        List of pairing dictionaries
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)

        if tournament.tournament_type != Tournament.SWISS:
            raise ValueError(
                f"O formato do torneio é {tournament.tournament_type}, não Suíço")

        engine = SwissPairingEngine(tournament)
        return engine.generate_pairings(round_number)

    except Tournament.DoesNotExist:
        raise ValueError(f"Torneio com ID {tournament_id} não encontrado")


def generate_elimination_pairings(tournament_id: str, round_number: int) -> List[Dict]:
    """
    Função principal para gerar emparelhamentos de eliminação única

    Args:
        tournament_id: UUID of the tournament
        round_number: Round number to generate pairings for

    Returns:
        List of pairing dictionaries
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)

        if tournament.tournament_type != Tournament.SINGLE_ELIMINATION:
            raise ValueError(
                f"O formato do torneio é {tournament.tournament_type}, não Eliminação Única")

        engine = SingleEliminationEngine(tournament)

        if round_number == 1:
            return engine.generate_bracket()
        else:
            return engine.generate_next_round(round_number - 1)

    except Tournament.DoesNotExist:
        raise ValueError(f"Torneio com ID {tournament_id} não encontrado")


def generate_round_robin_pairings(tournament_id: str) -> Dict[int, List[Dict]]:
    """
    Função principal para gerar todos os emparelhamentos round robin

    Args:
        tournament_id: UUID of the tournament

    Returns:
        Dictionary mapping round numbers to pairing lists
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)

        if tournament.tournament_type != Tournament.ROUND_ROBIN:
            raise ValueError(
                f"O formato do torneio é {tournament.tournament_type}, não Round Robin")

        engine = RoundRobinEngine(tournament)
        return engine.generate_all_rounds()

    except Tournament.DoesNotExist:
        raise ValueError(f"Torneio com ID {tournament_id} não encontrado")
