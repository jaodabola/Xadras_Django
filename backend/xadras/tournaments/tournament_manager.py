# XADRAS - Tournament Management Logic
# Implementation by Tournament Logic AI
# Priority: CRITICAL - Tournament state transitions, round progression, board assignment

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
    Central tournament management class

    Responsibilities:
    - Tournament state transitions
    - Round progression logic
    - Pairing generation and game creation
    - Board assignment integration
    - Result validation and processing
    """

    def __init__(self, tournament: Tournament):
        self.tournament = tournament

    def start_tournament(self, started_by: User) -> Dict:
        """
        Start a tournament

        Args:
            started_by: User starting the tournament (must be organizer)

        Returns:
            Dictionary with tournament status and first round info
        """
        logger.info(f"Starting tournament {self.tournament.name}")

        # Validate permissions
        if self.tournament.created_by != started_by:
            raise PermissionError(
                "Only tournament organizer can start tournament")

        # Validate tournament state
        if not self.tournament.can_start:
            raise ValueError(
                "Tournament cannot be started (check participant count and registration deadline)")

        with transaction.atomic():
            # Update tournament status
            self.tournament.status = Tournament.IN_PROGRESS
            self.tournament.start_date = timezone.now()

            # Calculate total rounds based on format
            self._calculate_total_rounds()
            self.tournament.save()

            # Assign seeds based on initial rating
            self._assign_seeds()

            # Generate first round
            first_round_result = self.generate_next_round()

            logger.info(
                f"Tournament {self.tournament.name} started successfully")

            return {
                'tournament_id': str(self.tournament.id),
                'status': self.tournament.status,
                'total_rounds': self.tournament.total_rounds,
                'current_round': self.tournament.current_round,
                'first_round': first_round_result
            }

    def generate_next_round(self) -> Dict:
        """
        Generate the next round of pairings

        Returns:
            Dictionary with round information and pairings
        """
        if self.tournament.status != Tournament.IN_PROGRESS:
            raise ValueError("Tournament is not in progress")

        next_round_number = self.tournament.current_round + 1

        logger.info(
            f"Generating round {next_round_number} for tournament {self.tournament.name}")

        # Check if tournament is finished
        if self._is_tournament_finished():
            return self._finish_tournament()

        with transaction.atomic():
            # Create new round
            tournament_round = TournamentRound.objects.create(
                tournament=self.tournament,
                round_number=next_round_number,
                status=TournamentRound.PENDING
            )

            # Generate pairings based on tournament format
            pairings_data = self._generate_pairings_for_round(
                next_round_number)

            # Create pairing objects and games
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

            # Update tournament current round
            self.tournament.current_round = next_round_number
            self.tournament.save()

            # Start the round
            self.start_round(next_round_number)

            logger.info(
                f"Generated round {next_round_number} with {len(created_pairings)} pairings")

            return {
                'round_number': next_round_number,
                'round_id': str(tournament_round.id),
                'pairings_count': len(created_pairings),
                'games_count': len([p for p in created_pairings if not p.is_bye]),
                'pairings': [self._serialize_pairing(p) for p in created_pairings]
            }

    def start_round(self, round_number: int) -> Dict:
        """
        Start a specific round

        Args:
            round_number: The round to start

        Returns:
            Dictionary with round status
        """
        try:
            tournament_round = TournamentRound.objects.get(
                tournament=self.tournament,
                round_number=round_number
            )
        except TournamentRound.DoesNotExist:
            raise ValueError(f"Round {round_number} not found")

        if tournament_round.status != TournamentRound.PENDING:
            raise ValueError(f"Round {round_number} is not in pending status")

        with transaction.atomic():
            tournament_round.status = TournamentRound.IN_PROGRESS
            tournament_round.start_time = timezone.now()
            tournament_round.save()

            # Start all games in this round
            games_started = 0
            for pairing in tournament_round.pairings.all():
                if pairing.game:
                    pairing.game.status = Game.IN_PROGRESS
                    pairing.game.save()
                    games_started += 1

        logger.info(f"Started round {round_number} with {games_started} games")

        return {
            'round_number': round_number,
            'status': tournament_round.status,
            'games_started': games_started,
            'start_time': tournament_round.start_time
        }

    def process_game_result(self, game: Game) -> Dict:
        """
        Process a completed game result and update tournament standings

        Args:
            game: The completed game

        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing game result for game {game.id}")

        try:
            pairing = TournamentPairing.objects.get(game=game)
        except TournamentPairing.DoesNotExist:
            raise ValueError(f"No tournament pairing found for game {game.id}")

        if pairing.round.tournament != self.tournament:
            raise ValueError("Game does not belong to this tournament")

        with transaction.atomic():
            # Update pairing result based on game result
            pairing.update_result_from_game()

            # Check if round is complete
            round_complete = pairing.round.is_complete

            # Update tiebreakers
            update_participant_tiebreakers(str(self.tournament.id))

            result = {
                'pairing_id': str(pairing.id),
                'result': pairing.result,
                'round_complete': round_complete,
                'tournament_complete': False
            }

            # If round is complete, check if tournament is finished
            if round_complete:
                pairing.round.status = TournamentRound.COMPLETED
                pairing.round.end_time = timezone.now()
                pairing.round.save()

                if self._is_tournament_finished():
                    self._finish_tournament()
                    result['tournament_complete'] = True

            logger.info(f"Processed game result: {pairing.result}")
            return result

    def get_current_standings(self) -> List[Dict]:
        """Get current tournament standings"""
        return calculate_tournament_standings(str(self.tournament.id))

    def get_round_pairings(self, round_number: int) -> List[Dict]:
        """
        Get pairings for a specific round

        Args:
            round_number: The round number

        Returns:
            List of pairing dictionaries
        """
        try:
            tournament_round = TournamentRound.objects.get(
                tournament=self.tournament,
                round_number=round_number
            )
        except TournamentRound.DoesNotExist:
            raise ValueError(f"Round {round_number} not found")

        pairings = tournament_round.pairings.all().order_by('board_number')
        return [self._serialize_pairing(p) for p in pairings]

    def assign_boards_to_round(self, round_number: int, board_assignments: Dict[str, int]) -> Dict:
        """
        Assign physical boards to pairings in a round

        Args:
            round_number: The round number
            board_assignments: Dictionary mapping pairing_id to board_number

        Returns:
            Dictionary with assignment results
        """
        try:
            tournament_round = TournamentRound.objects.get(
                tournament=self.tournament,
                round_number=round_number
            )
        except TournamentRound.DoesNotExist:
            raise ValueError(f"Round {round_number} not found")

        assignments_made = 0

        with transaction.atomic():
            for pairing_id, assignment_data in board_assignments.items():
                try:
                    pairing = tournament_round.pairings.get(id=pairing_id)
                    if not pairing.is_bye:
                        # Support both old format (just board_number) and new format (dict with Vision AI fields)
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
                        f"Pairing {pairing_id} not found for board assignment")

        logger.info(
            f"Assigned {assignments_made} boards for round {round_number}")

        return {
            'round_number': round_number,
            'assignments_made': assignments_made,
            'total_requested': len(board_assignments)
        }

    def _calculate_total_rounds(self):
        """Calculate total rounds based on tournament format and participants"""
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
        """Assign seeds to participants based on initial rating"""
        participants = self.tournament.participants.filter(
            is_active=True).order_by('-initial_rating')

        for i, participant in enumerate(participants, 1):
            participant.seed = i
            participant.save(update_fields=['seed'])

    def _generate_pairings_for_round(self, round_number: int) -> List[Dict]:
        """Generate pairings based on tournament format"""
        tournament_id = str(self.tournament.id)

        if self.tournament.tournament_type == Tournament.SWISS:
            return generate_swiss_pairings(tournament_id, round_number)
        elif self.tournament.tournament_type == Tournament.SINGLE_ELIMINATION:
            return generate_elimination_pairings(tournament_id, round_number)
        elif self.tournament.tournament_type == Tournament.ROUND_ROBIN:
            # For round robin, we need to get the specific round from all rounds
            all_rounds = generate_round_robin_pairings(tournament_id)
            return all_rounds.get(round_number, [])
        else:
            raise ValueError(
                f"Unsupported tournament format: {self.tournament.tournament_type}")

    def _create_pairing_from_data(self, tournament_round: TournamentRound, pairing_data: Dict, board_number: int) -> TournamentPairing:
        """Create a TournamentPairing object from pairing data"""
        pairing = TournamentPairing.objects.create(
            round=tournament_round,
            white_player=pairing_data.get('white_player'),
            black_player=pairing_data.get('black_player'),
            bye_player=pairing_data.get('bye_player'),
            board_number=board_number if not pairing_data.get(
                'is_bye') else None
        )

        # Create game if not a bye
        if not pairing_data.get('is_bye'):
            game = Game.objects.create(
                white_player=pairing_data['white_player'],
                black_player=pairing_data['black_player'],
                status=Game.PENDING
            )
            pairing.game = game
            pairing.save()
        else:
            # Process bye immediately
            pairing.result = TournamentPairing.BYE
            pairing.save()
            pairing._update_participant_scores()

        return pairing

    def _is_tournament_finished(self) -> bool:
        """Check if tournament should be finished"""
        if self.tournament.tournament_type == Tournament.SINGLE_ELIMINATION:
            # Tournament is finished when only one player remains
            active_participants = self.tournament.participants.filter(
                is_active=True).count()
            return active_participants <= 1
        elif self.tournament.tournament_type in [Tournament.SWISS, Tournament.ROUND_ROBIN]:
            # Tournament is finished when all planned rounds are complete
            return self.tournament.current_round >= self.tournament.total_rounds

        return False

    def _finish_tournament(self) -> Dict:
        """Finish the tournament and determine final standings"""
        logger.info(f"Finishing tournament {self.tournament.name}")

        with transaction.atomic():
            self.tournament.status = Tournament.FINISHED
            self.tournament.end_time = timezone.now()
            self.tournament.save()

            # Calculate final standings
            final_standings = self.get_current_standings()

            logger.info(f"Tournament {self.tournament.name} finished")

            return {
                'tournament_finished': True,
                'final_standings': final_standings,
                'winner': final_standings[0] if final_standings else None
            }

    def _serialize_pairing(self, pairing: TournamentPairing) -> Dict:
        """Serialize a pairing object to dictionary"""
        return pairing.to_dict()


# Utility functions for external use

def start_tournament(tournament_id: str, started_by_user_id: int) -> Dict:
    """
    Start a tournament

    Args:
        tournament_id: UUID of the tournament
        started_by_user_id: ID of user starting the tournament

    Returns:
        Dictionary with tournament start results
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        user = User.objects.get(id=started_by_user_id)

        manager = TournamentManager(tournament)
        return manager.start_tournament(user)

    except Tournament.DoesNotExist:
        raise ValueError(f"Tournament with ID {tournament_id} not found")
    except User.DoesNotExist:
        raise ValueError(f"User with ID {started_by_user_id} not found")


def generate_tournament_round(tournament_id: str) -> Dict:
    """
    Generate next round for a tournament

    Args:
        tournament_id: UUID of the tournament

    Returns:
        Dictionary with round generation results
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        manager = TournamentManager(tournament)
        return manager.generate_next_round()

    except Tournament.DoesNotExist:
        raise ValueError(f"Tournament with ID {tournament_id} not found")


def process_tournament_game_result(game_id: int) -> Dict:
    """
    Process a completed game result for tournament

    Args:
        game_id: ID of the completed game

    Returns:
        Dictionary with processing results
    """
    try:
        game = Game.objects.get(id=game_id)

        # Find tournament pairing for this game
        pairing = TournamentPairing.objects.get(game=game)
        tournament = pairing.round.tournament

        manager = TournamentManager(tournament)
        return manager.process_game_result(game)

    except Game.DoesNotExist:
        raise ValueError(f"Game with ID {game_id} not found")
    except TournamentPairing.DoesNotExist:
        raise ValueError(f"No tournament pairing found for game {game_id}")


def get_tournament_standings(tournament_id: str) -> List[Dict]:
    """
    Get current standings for a tournament

    Args:
        tournament_id: UUID of the tournament

    Returns:
        List of standings dictionaries
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        manager = TournamentManager(tournament)
        return manager.get_current_standings()

    except Tournament.DoesNotExist:
        raise ValueError(f"Tournament with ID {tournament_id} not found")
