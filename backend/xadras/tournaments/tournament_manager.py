# XADRAS - Lógica de Gestão de Torneios
# Implementação pela Tournament Logic AI
# Prioridade: CRÍTICA - Transições de estado do torneio, progressão de rondas, atribuição de tabuleiros

from django.db import transaction, models
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Tournament, TournamentParticipant, TournamentRound, TournamentPairing
from game.models import Game
from .pairing_algorithms import (
    generate_swiss_pairings,
    generate_elimination_pairings,
    generate_round_robin_pairings
)
from .standings_calculator import calculate_tournament_standings, update_participant_tiebreakers
import logging
from typing import List, Dict, Optional

User = get_user_model()
logger = logging.getLogger(__name__)


class TournamentManager:
    """
    Classe central de gestão de torneios

    Responsabilidades:
    - Transições de estado do torneio
    - Lógica de progressão de rondas
    - Geração de emparelhamentos e criação de jogos
    - Integração de atribuição de tabuleiros
    - Validação e processamento de resultados
    """

    def __init__(self, tournament: Tournament):
        self.tournament = tournament

    def start_tournament(self, started_by: User) -> Dict:
        """
        Iniciar um torneio

        Args:
            started_by: Utilizador que inicia o torneio (deve ser o organizador)

        Retorna:
            Dicionário com o estado do torneio e informação da primeira ronda
        """
        logger.info(f"Iniciando o torneio {self.tournament.name}")

        # Validar permissões
        if self.tournament.created_by != started_by:
            raise PermissionError(
                "Apenas o organizador do torneio pode iniciar o torneio")

        # Validar estado do torneio
        if not self.tournament.can_start:
            raise ValueError(
                "O torneio não pode ser iniciado (verifique o número de participantes e o prazo de inscrição)")

        with transaction.atomic():
            # Atualizar estado do torneio
            self.tournament.status = Tournament.IN_PROGRESS
            self.tournament.start_date = timezone.now()

            # Calcular total de rondas com base no formato
            self._calculate_total_rounds()
            self.tournament.save()

            # Atribuir sementes (seeds) com base no rating inicial
            self._assign_seeds()

            # Gerar a primeira ronda
            first_round_result = self.generate_next_round()

            logger.info(
                f"Torneio {self.tournament.name} iniciado com sucesso")

            return {
                'tournament_id': str(self.tournament.id),
                'status': self.tournament.status,
                'total_rounds': self.tournament.total_rounds,
                'current_round': self.tournament.current_round,
                'first_round': first_round_result
            }

    def generate_next_round(self) -> Dict:
        """
        Gerar a próxima ronda de emparelhamentos

        Retorna:
            Dicionário com informações da ronda e emparelhamentos
        """
        if self.tournament.status != Tournament.IN_PROGRESS:
            raise ValueError("O torneio não está em curso")

        next_round_number = self.tournament.current_round + 1

        logger.info(
            f"Gerando a ronda {next_round_number} para o torneio {self.tournament.name}")

        # Verificar se o torneio terminou
        if self._is_tournament_finished():
            return self._finish_tournament()

        with transaction.atomic():
            # Criar nova ronda
            tournament_round = TournamentRound.objects.create(
                tournament=self.tournament,
                round_number=next_round_number,
                status=TournamentRound.PENDING
            )

            # Gerar emparelhamentos com base no formato do torneio
            pairings_data = self._generate_pairings_for_round(
                next_round_number)

            # Criar objetos de emparelhamento e jogos
            created_pairings = []
            board_number = 1

            for pairing_data in pairings_data:
                pairing = self._create_pairing_from_data(
                    tournament_round,
                    pairing_data,
                    board_number
                )
                created_pairings.append(pairing)

                if not pairing.is_bye:
                    board_number += 1

            # Atualizar a ronda atual do torneio
            self.tournament.current_round = next_round_number
            self.tournament.save()

            # Iniciar a ronda
            self.start_round(next_round_number)

            logger.info(
                f"Gerada a ronda {next_round_number} com {len(created_pairings)} emparelhamentos")

            return {
                'round_number': next_round_number,
                'round_id': str(tournament_round.id),
                'pairings_count': len(created_pairings),
                'games_count': len([p for p in created_pairings if not p.is_bye]),
                'pairings': [self._serialize_pairing(p) for p in created_pairings]
            }

    def start_round(self, round_number: int) -> Dict:
        """
        Iniciar uma ronda específica

        Args:
            round_number: A ronda a iniciar

        Retorna:
            Dicionário com o estado da ronda
        """
        try:
            tournament_round = TournamentRound.objects.get(
                tournament=self.tournament,
                round_number=round_number
            )
        except TournamentRound.DoesNotExist:
            raise ValueError(f"Ronda {round_number} não encontrada")

        if tournament_round.status != TournamentRound.PENDING:
            raise ValueError(f"A ronda {round_number} não está em estado pendente")

        with transaction.atomic():
            tournament_round.status = TournamentRound.IN_PROGRESS
            tournament_round.start_time = timezone.now()
            tournament_round.save()

            # Iniciar todos os jogos nesta ronda
            games_started = 0
            for pairing in tournament_round.pairings.all():
                if pairing.game:
                    pairing.game.status = Game.IN_PROGRESS
                    pairing.game.save()
                    games_started += 1

        logger.info(f"Iniciada a ronda {round_number} com {games_started} jogos")

        return {
            'round_number': round_number,
            'status': tournament_round.status,
            'games_started': games_started,
            'start_time': tournament_round.start_time
        }

    def process_game_result(self, game: Game) -> Dict:
        """
        Processar o resultado de um jogo concluído e atualizar a classificação do torneio

        Args:
            game: O jogo concluído

        Retorna:
            Dicionário com os resultados do processamento
        """
        logger.info(f"Processando resultado do jogo {game.id}")

        try:
            pairing = TournamentPairing.objects.get(game=game)
        except TournamentPairing.DoesNotExist:
            raise ValueError(f"Nenhum emparelhamento de torneio encontrado para o jogo {game.id}")

        if pairing.round.tournament != self.tournament:
            raise ValueError("O jogo não pertence a este torneio")

        with transaction.atomic():
            # Atualizar resultado do emparelhamento com base no resultado do jogo
            pairing.update_result_from_game()

            # Verificar se a ronda está concluída
            round_complete = pairing.round.is_complete

            # Atualizar desempates
            update_participant_tiebreakers(str(self.tournament.id))

            result = {
                'pairing_id': str(pairing.id),
                'result': pairing.result,
                'round_complete': round_complete,
                'tournament_complete': False
            }

            # Se a ronda estiver concluída, verificar se o torneio terminou
            if round_complete:
                pairing.round.status = TournamentRound.COMPLETED
                pairing.round.end_time = timezone.now()
                pairing.round.save()

                if self._is_tournament_finished():
                    self._finish_tournament()
                    result['tournament_complete'] = True

            logger.info(f"Resultado do jogo processado: {pairing.result}")
            return result

    def get_current_standings(self) -> List[Dict]:
        """Obter a classificação atual do torneio"""
        return calculate_tournament_standings(str(self.tournament.id))

    def get_round_pairings(self, round_number: int) -> List[Dict]:
        """
        Obter emparelhamentos para uma ronda específica

        Args:
            round_number: O número da ronda

        Retorna:
            Lista de dicionários de emparelhamento
        """
        try:
            tournament_round = TournamentRound.objects.get(
                tournament=self.tournament,
                round_number=round_number
            )
        except TournamentRound.DoesNotExist:
            raise ValueError(f"Ronda {round_number} não encontrada")

        pairings = tournament_round.pairings.all().order_by('board_number')
        return [self._serialize_pairing(p) for p in pairings]

    def assign_boards_to_round(self, round_number: int, board_assignments: Dict[str, int]) -> Dict:
        """
        Atribuir tabuleiros físicos a emparelhamentos numa ronda

        Args:
            round_number: O número da ronda
            board_assignments: Dicionário mapeando pairing_id para board_number

        Retorna:
            Dicionário com os resultados da atribuição
        """
        try:
            tournament_round = TournamentRound.objects.get(
                tournament=self.tournament,
                round_number=round_number
            )
        except TournamentRound.DoesNotExist:
            raise ValueError(f"Ronda {round_number} não encontrada")

        assignments_made = 0

        with transaction.atomic():
            for pairing_id, assignment_data in board_assignments.items():
                try:
                    pairing = tournament_round.pairings.get(id=pairing_id)
                    if not pairing.is_bye:
                        # Suporta tanto o formato antigo (apenas board_number) quanto o novo (dicionário com campos de IA de Visão)
                        if isinstance(assignment_data, dict):
                            pairing.physical_board_id = assignment_data.get(
                                'physical_board_id')
                            pairing.camera_id = assignment_data.get(
                                'camera_id')
                            pairing.board_number = assignment_data.get(
                                'board_number', pairing.board_number)
                        else:
                            # Legacy support: assignment_data is just board_number
                            pairing.board_number = assignment_data

                        pairing.save()
                        assignments_made += 1
                except TournamentPairing.DoesNotExist:
                    logger.warning(
                        f"Emparelhamento {pairing_id} não encontrado para atribuição de tabuleiro")

        logger.info(
            f"Atribuídos {assignments_made} tabuleiros para a ronda {round_number}")

        return {
            'round_number': round_number,
            'assignments_made': assignments_made,
            'total_requested': len(board_assignments)
        }

    def _calculate_total_rounds(self):
        """Calcular o total de rondas com base no formato do torneio e participantes"""
        participant_count = self.tournament.participant_count

        if self.tournament.tournament_type == Tournament.SWISS:
            # Swiss: ceil(log2(participants)) rounds
            import math
            self.tournament.total_rounds = max(
                1, math.ceil(math.log2(participant_count)))
        elif self.tournament.tournament_type == Tournament.SINGLE_ELIMINATION:
            # Single elimination: ceil(log2(participants)) rounds
            import math
            self.tournament.total_rounds = max(
                1, math.ceil(math.log2(participant_count)))
        elif self.tournament.tournament_type == Tournament.ROUND_ROBIN:
            # Round robin: n-1 rounds for n players (or n if odd)
            self.tournament.total_rounds = participant_count - \
                1 if participant_count % 2 == 0 else participant_count

    def _assign_seeds(self):
        """Atribuir sementes (seeds) aos participantes com base no rating inicial"""
        participants = self.tournament.participants.filter(
            is_active=True).order_by('-initial_rating')

        for i, participant in enumerate(participants, 1):
            participant.seed = i
            participant.save(update_fields=['seed'])

    def _generate_pairings_for_round(self, round_number: int) -> List[Dict]:
        """Gerar emparelhamentos com base no formato do torneio"""
        tournament_id = str(self.tournament.id)

        if self.tournament.tournament_type == Tournament.SWISS:
            return generate_swiss_pairings(tournament_id, round_number)
        elif self.tournament.tournament_type == Tournament.SINGLE_ELIMINATION:
            return generate_elimination_pairings(tournament_id, round_number)
        elif self.tournament.tournament_type == Tournament.ROUND_ROBIN:
            # Para round robin, precisamos de obter a ronda específica de todas as rondas
            all_rounds = generate_round_robin_pairings(tournament_id)
            return all_rounds.get(round_number, [])
        else:
            raise ValueError(
                f"Formato de torneio não suportado: {self.tournament.tournament_type}")

    def _create_pairing_from_data(self, tournament_round: TournamentRound, pairing_data: Dict, board_number: int) -> TournamentPairing:
        """Criar um objeto TournamentPairing a partir dos dados do emparelhamento"""
        pairing = TournamentPairing.objects.create(
            round=tournament_round,
            white_player=pairing_data.get('white_player'),
            black_player=pairing_data.get('black_player'),
            bye_player=pairing_data.get('bye_player'),
            board_number=board_number if not pairing_data.get(
                'is_bye') else None
        )

        # Criar jogo se não for um bye
        if not pairing_data.get('is_bye'):
            game = Game.objects.create(
                white_player=pairing_data['white_player'],
                black_player=pairing_data['black_player'],
                status=Game.PENDING
            )
            pairing.game = game
            pairing.save()
        else:
            # Processar bye imediatamente
            pairing.result = TournamentPairing.BYE
            pairing.save()
            pairing._update_participant_scores()

        return pairing

    def _is_tournament_finished(self) -> bool:
        """Verificar se o torneio deve terminar"""
        if self.tournament.tournament_type == Tournament.SINGLE_ELIMINATION:
            # O torneio termina quando resta apenas um jogador
            active_participants = self.tournament.participants.filter(
                is_active=True).count()
            return active_participants <= 1
        elif self.tournament.tournament_type in [Tournament.SWISS, Tournament.ROUND_ROBIN]:
            # O torneio termina quando todas as rondas planeadas estiverem concluídas
            return self.tournament.current_round >= self.tournament.total_rounds

        return False

    def _finish_tournament(self) -> Dict:
        """Terminar o torneio e determinar a classificação final"""
        logger.info(f"Terminando o torneio {self.tournament.name}")

        with transaction.atomic():
            self.tournament.status = Tournament.FINISHED
            self.tournament.end_time = timezone.now()
            self.tournament.save()

            # Calcular classificação final
            final_standings = self.get_current_standings()

            logger.info(f"Torneio {self.tournament.name} terminado")

            return {
                'tournament_finished': True,
                'final_standings': final_standings,
                'winner': final_standings[0] if final_standings else None
            }

    def _serialize_pairing(self, pairing: TournamentPairing) -> Dict:
        """Serializar um objeto de emparelhamento para dicionário"""
        return pairing.to_dict()


# Funções utilitárias para uso externo

def start_tournament(tournament_id: str, started_by_user_id: int) -> Dict:
    """
    Iniciar um torneio

    Args:
        tournament_id: UUID do torneio
        started_by_user_id: ID do utilizador que inicia o torneio

    Retorna:
        Dicionário com os resultados do início do torneio
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        user = User.objects.get(id=started_by_user_id)

        manager = TournamentManager(tournament)
        return manager.start_tournament(user)

    except Tournament.DoesNotExist:
        raise ValueError(f"Torneio com ID {tournament_id} não encontrado")
    except User.DoesNotExist:
        raise ValueError(f"Utilizador com ID {started_by_user_id} não encontrado")


def generate_tournament_round(tournament_id: str) -> Dict:
    """
    Gerar a próxima ronda para um torneio

    Args:
        tournament_id: UUID do torneio

    Retorna:
        Dicionário com os resultados da geração da ronda
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        manager = TournamentManager(tournament)
        return manager.generate_next_round()

    except Tournament.DoesNotExist:
        raise ValueError(f"Torneio com ID {tournament_id} não encontrado")


def process_tournament_game_result(game_id: int) -> Dict:
    """
    Processar o resultado de um jogo concluído para o torneio

    Args:
        game_id: ID do jogo concluído

    Retorna:
        Dicionário com os resultados do processamento
    """
    try:
        game = Game.objects.get(id=game_id)

        # Encontrar o emparelhamento de torneio para este jogo
        pairing = TournamentPairing.objects.get(game=game)
        tournament = pairing.round.tournament

        manager = TournamentManager(tournament)
        return manager.process_game_result(game)

    except Game.DoesNotExist:
        raise ValueError(f"Jogo com ID {game_id} não encontrado")
    except TournamentPairing.DoesNotExist:
        raise ValueError(f"Nenhum emparelhamento de torneio encontrado para o jogo {game_id}")


def get_tournament_standings(tournament_id: str) -> List[Dict]:
    """
    Obter a classificação atual para um torneio

    Args:
        tournament_id: UUID do torneio

    Retorna:
        Lista de dicionários de classificação
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        manager = TournamentManager(tournament)
        return manager.get_current_standings()

    except Tournament.DoesNotExist:
        raise ValueError(f"Torneio com ID {tournament_id} não encontrado")
