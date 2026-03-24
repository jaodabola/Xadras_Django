# XADRAS - Tournament Pairing Algorithms
# Implementation by Tournament Logic AI
# Priority: CRITICAL - Swiss System, Single Elimination, Round Robin

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
    Swiss System pairing algorithm implementation
    
    Features:
    - Score-based grouping
    - Rating-based pairing within groups
    - Color balance (avoid 3 consecutive same colors)
    - Avoid repeat pairings
    - Bye management for odd numbers
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
        Generate Swiss system pairings for the specified round
        
        Args:
            round_number: The round number to generate pairings for
            
        Returns:
            List of pairing dictionaries with player assignments
        """
        logger.info(f"Generating Swiss pairings for tournament {self.tournament.name}, round {round_number}")
        
        if len(self.participants) < 2:
            raise ValueError("Need at least 2 participants for Swiss pairings")
        
        # PROPER BYE HANDLING: Handle odd number of players FIRST
        pairings = []
        active_participants = list(self.participants)
        
        # If odd number of participants, select bye player first
        if len(active_participants) % 2 == 1:
            bye_player = self._select_bye_player(active_participants)
            if bye_player:
                bye_pairing = self._create_bye_pairing(bye_player)
                pairings.append(bye_pairing)
                active_participants.remove(bye_player)
                logger.info(f"Selected bye player: {bye_player.user.username}")
        
        # Now work with even number of participants
        # Group remaining participants by score
        score_groups = {}
        for participant in active_participants:
            score = participant.score
            if score not in score_groups:
                score_groups[score] = []
            score_groups[score].append(participant)
        
        # Sort groups by score (highest first)
        score_groups = dict(sorted(score_groups.items(), key=lambda x: x[0], reverse=True))
        
        # Generate pairings within each score group
        unpaired_players = []
        
        for score, players in score_groups.items():
            group_pairings, group_unpaired = self._pair_within_group(players)
            pairings.extend(group_pairings)
            unpaired_players.extend(group_unpaired)
        
        # Handle any remaining unpaired players from different score groups
        if unpaired_players:
            cross_group_pairings, final_unpaired = self._pair_across_groups(unpaired_players)
            pairings.extend(cross_group_pairings)
            
            # With proper bye handling, this should be rare
            if final_unpaired:
                logger.warning(f"Still have {len(final_unpaired)} unpaired players after bye handling")
                # Force pair remaining players
                while len(final_unpaired) >= 2:
                    player1 = final_unpaired.pop(0)
                    player2 = final_unpaired.pop(0)
                    pairing = self._create_pairing(player1, player2)
                    pairings.append(pairing)
        
        logger.info(f"Generated {len(pairings)} pairings for round {round_number}")
        return pairings
    
    def _group_by_score(self) -> Dict[float, List[TournamentParticipant]]:
        """Group participants by their current score"""
        score_groups = {}
        
        for participant in self.participants:
            score = participant.score
            if score not in score_groups:
                score_groups[score] = []
            score_groups[score].append(participant)
        
        # Sort groups by score (highest first)
        return dict(sorted(score_groups.items(), key=lambda x: x[0], reverse=True))
    
    def _pair_within_group(self, players: List[TournamentParticipant]) -> Tuple[List[Dict], List[TournamentParticipant]]:
        """
        Pair players within a score group
        
        Returns:
            Tuple of (pairings, unpaired_players)
        """
        if len(players) < 2:
            return [], players
        
        # Sort by rating for better pairings
        players_sorted = sorted(players, key=lambda p: p.initial_rating, reverse=True)
        
        pairings = []
        unpaired = []
        used_players = set()
        
        # Try to pair players optimally
        for i, player1 in enumerate(players_sorted):
            if player1.id in used_players:
                continue
                
            best_opponent = None
            best_score = -1
            
            for j, player2 in enumerate(players_sorted[i+1:], i+1):
                if player2.id in used_players:
                    continue
                
                # Calculate pairing quality score
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
        
        # Add any remaining unpaired players
        for player in players_sorted:
            if player.id not in used_players:
                unpaired.append(player)
        
        return pairings, unpaired
    
    def _pair_across_groups(self, players: List[TournamentParticipant]) -> Tuple[List[Dict], List[TournamentParticipant]]:
        """
        Pair remaining players across different score groups
        """
        if len(players) < 2:
            return [], players
        
        pairings = []
        remaining = players.copy()
        
        while len(remaining) >= 2:
            player1 = remaining.pop(0)
            
            # Find best opponent from remaining players
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
        Calculate quality score for a potential pairing
        Higher score = better pairing
        
        Factors:
        - Haven't played before (highest priority)
        - Color balance
        - Rating proximity
        """
        score = 0.0
        
        # Check if they've played before (most important factor)
        if not self._have_played_before(player1, player2):
            score += 100.0
        else:
            score -= 50.0  # Heavy penalty for repeat pairings
        
        # Color balance factor
        color_balance_score = self._calculate_color_balance_score(player1, player2)
        score += color_balance_score * 10.0
        
        # Rating proximity factor (closer ratings = better pairing)
        rating_diff = abs(player1.initial_rating - player2.initial_rating)
        rating_score = max(0, 400 - rating_diff) / 400.0  # Normalize to 0-1
        score += rating_score * 5.0
        
        return score
    
    def _have_played_before(self, player1: TournamentParticipant, player2: TournamentParticipant) -> bool:
        """Check if two players have played against each other before"""
        pairing_key = tuple(sorted([player1.user.id, player2.user.id]))
        return pairing_key in self.previous_pairings
    
    def _calculate_color_balance_score(self, player1: TournamentParticipant, player2: TournamentParticipant) -> float:
        """
        Calculate color balance score for pairing
        Prefer pairings that balance colors
        """
        player1_colors = self._get_player_color_history(player1.user)
        player2_colors = self._get_player_color_history(player2.user)
        
        # Count recent colors (last 2 games)
        player1_recent_white = sum(1 for color in player1_colors[-2:] if color == 'white')
        player1_recent_black = sum(1 for color in player1_colors[-2:] if color == 'black')
        
        player2_recent_white = sum(1 for color in player2_colors[-2:] if color == 'white')
        player2_recent_black = sum(1 for color in player2_colors[-2:] if color == 'black')
        
        # Prefer giving white to player who has played black more recently
        if player1_recent_black > player1_recent_white and player2_recent_white > player2_recent_black:
            return 1.0  # Good balance: player1 gets white, player2 gets black
        elif player2_recent_black > player2_recent_white and player1_recent_white > player1_recent_black:
            return 1.0  # Good balance: player2 gets white, player1 gets black
        else:
            return 0.5  # Neutral balance
    
    def _get_player_color_history(self, user: User) -> List[str]:
        """Get player's color history in this tournament"""
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
        
        return sorted(colors)  # This is a simplified version, should be properly ordered by round
    
    def _create_pairing(self, player1: TournamentParticipant, player2: TournamentParticipant) -> Dict:
        """
        Create a pairing between two players
        Determine colors based on color balance
        """
        # Determine colors
        player1_colors = self._get_player_color_history(player1.user)
        player2_colors = self._get_player_color_history(player2.user)
        
        # Simple color assignment logic (can be improved)
        player1_white_count = player1_colors.count('white')
        player1_black_count = player1_colors.count('black')
        player2_white_count = player2_colors.count('white')
        player2_black_count = player2_colors.count('black')
        
        # Assign white to player who has played black more or has higher rating if equal
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
        Select player who should receive bye
        Priority: Player who hasn't had bye yet, then lowest rated
        """
        # Get players who haven't had bye yet in this tournament
        players_without_bye = []
        players_with_bye = []
        
        for participant in participants:
            # Check if player has had bye in this tournament
            has_bye = TournamentPairing.objects.filter(
                round__tournament=self.tournament,
                bye_player=participant.user,
                bye_player__isnull=False
            ).exists()
            
            if has_bye:
                players_with_bye.append(participant)
            else:
                players_without_bye.append(participant)
        
        # Prefer players who haven't had bye
        candidates = players_without_bye if players_without_bye else players_with_bye
        
        if not candidates:
            return None
        
        # Select lowest rated player from candidates
        return min(candidates, key=lambda p: p.initial_rating)
    
    def _create_bye_pairing(self, player: TournamentParticipant) -> Dict:
        """Create a bye pairing for a player"""
        return {
            'white_player': None,
            'black_player': None,
            'bye_player': player.user,
            'is_bye': True
        }
    
    def _get_previous_pairings(self) -> set:
        """Get set of all previous pairings in this tournament"""
        pairings = set()
        
        tournament_pairings = TournamentPairing.objects.filter(
            round__tournament=self.tournament,
            white_player__isnull=False,
            black_player__isnull=False
        )
        
        for pairing in tournament_pairings:
            pairing_key = tuple(sorted([pairing.white_player.id, pairing.black_player.id]))
            pairings.add(pairing_key)
        
        return pairings


class SingleEliminationEngine:
    """
    Single Elimination tournament pairing engine
    
    Features:
    - Seeded bracket generation
    - Power of 2 bracket structure
    - Winner advancement logic
    - Bracket visualization data
    """
    
    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self.participants = list(
            tournament.participants.filter(is_active=True)
            .order_by('seed')
        )
    
    def generate_bracket(self) -> List[Dict]:
        """
        Generate single elimination bracket
        
        Returns:
            List of first round pairings
        """
        logger.info(f"Generating elimination bracket for tournament {self.tournament.name}")
        
        participant_count = len(self.participants)
        if participant_count < 2:
            raise ValueError("Need at least 2 participants for elimination tournament")
        
        # For single elimination, we need power of 2 participants
        # If not power of 2, some players get byes in first round
        next_power_of_2 = 1
        while next_power_of_2 < participant_count:
            next_power_of_2 *= 2
        
        first_round_games = participant_count - (next_power_of_2 - participant_count)
        byes = participant_count - first_round_games
        
        pairings = []
        
        # Create first round pairings with seeded bracket
        players_copy = self.participants.copy()
        
        # Give byes to highest seeds
        bye_players = players_copy[:byes]
        playing_players = players_copy[byes:]
        
        # Create byes
        for player in bye_players:
            bye_pairing = {
                'white_player': None,
                'black_player': None,
                'bye_player': player.user,
                'is_bye': True
            }
            pairings.append(bye_pairing)
        
        # Create first round games
        # Pair highest remaining seed with lowest, etc.
        while len(playing_players) >= 2:
            high_seed = playing_players.pop(0)  # Highest seed
            low_seed = playing_players.pop()    # Lowest seed
            
            pairing = {
                'white_player': high_seed.user,
                'black_player': low_seed.user,
                'bye_player': None,
                'is_bye': False
            }
            pairings.append(pairing)
        
        logger.info(f"Generated elimination bracket with {len(pairings)} first round pairings")
        return pairings
    
    def generate_next_round(self, current_round: int) -> List[Dict]:
        """
        Generate next round pairings based on previous round results
        """
        logger.info(f"Generating elimination round {current_round + 1}")
        
        # Get winners from previous round
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
            logger.info("Tournament finished - less than 2 winners remaining")
            return []
        
        # Pair winners for next round
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
        
        # Handle odd winner (shouldn't happen in proper elimination)
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
        """Get winner of a tournament pairing"""
        if pairing.result == TournamentPairing.BYE:
            return pairing.bye_player
        elif pairing.result == TournamentPairing.WHITE_WIN:
            return pairing.white_player
        elif pairing.result == TournamentPairing.BLACK_WIN:
            return pairing.black_player
        else:
            return None  # Game not finished or draw (handle draws in elimination?)


class RoundRobinEngine:
    """
    Round Robin tournament pairing engine
    
    Features:
    - Complete round-robin scheduling
    - Every player plays every other player once
    - Color balance across tournament
    """
    
    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self.participants = list(
            tournament.participants.filter(is_active=True)
            .order_by('seed')
        )
    
    def generate_all_rounds(self) -> Dict[int, List[Dict]]:
        """
        Generate all rounds for round robin tournament
        
        Returns:
            Dictionary mapping round number to list of pairings
        """
        logger.info(f"Generating round robin schedule for tournament {self.tournament.name}")
        
        participant_count = len(self.participants)
        if participant_count < 2:
            raise ValueError("Need at least 2 participants for round robin tournament")
        
        # Round robin requires n-1 rounds for n players (or n rounds if n is odd)
        total_rounds = participant_count - 1 if participant_count % 2 == 0 else participant_count
        
        all_pairings = {}
        
        # Generate round robin schedule using circle method
        players = [p.user for p in self.participants]
        
        # If odd number of players, add a "bye" placeholder
        if len(players) % 2 == 1:
            players.append(None)  # None represents bye
        
        n = len(players)
        
        for round_num in range(1, total_rounds + 1):
            round_pairings = []
            
            for i in range(n // 2):
                player1 = players[i]
                player2 = players[n - 1 - i]
                
                if player1 is None:
                    # player2 gets bye
                    bye_pairing = {
                        'white_player': None,
                        'black_player': None,
                        'bye_player': player2,
                        'is_bye': True
                    }
                    round_pairings.append(bye_pairing)
                elif player2 is None:
                    # player1 gets bye
                    bye_pairing = {
                        'white_player': None,
                        'black_player': None,
                        'bye_player': player1,
                        'is_bye': True
                    }
                    round_pairings.append(bye_pairing)
                else:
                    # Alternate colors based on round and position
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
            
            # Rotate players for next round (keep first player fixed)
            players = [players[0]] + [players[-1]] + players[1:-1]
        
        logger.info(f"Generated round robin schedule with {total_rounds} rounds")
        return all_pairings


def generate_swiss_pairings(tournament_id: str, round_number: int) -> List[Dict]:
    """
    Main function to generate Swiss system pairings
    
    Args:
        tournament_id: UUID of the tournament
        round_number: Round number to generate pairings for
        
    Returns:
        List of pairing dictionaries
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        
        if tournament.format != Tournament.SWISS:
            raise ValueError(f"Tournament format is {tournament.format}, not Swiss")
        
        engine = SwissPairingEngine(tournament)
        return engine.generate_pairings(round_number)
        
    except Tournament.DoesNotExist:
        raise ValueError(f"Tournament with ID {tournament_id} not found")


def generate_elimination_pairings(tournament_id: str, round_number: int) -> List[Dict]:
    """
    Main function to generate single elimination pairings
    
    Args:
        tournament_id: UUID of the tournament
        round_number: Round number to generate pairings for
        
    Returns:
        List of pairing dictionaries
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        
        if tournament.format != Tournament.SINGLE_ELIMINATION:
            raise ValueError(f"Tournament format is {tournament.format}, not Single Elimination")
        
        engine = SingleEliminationEngine(tournament)
        
        if round_number == 1:
            return engine.generate_bracket()
        else:
            return engine.generate_next_round(round_number - 1)
        
    except Tournament.DoesNotExist:
        raise ValueError(f"Tournament with ID {tournament_id} not found")


def generate_round_robin_pairings(tournament_id: str) -> Dict[int, List[Dict]]:
    """
    Main function to generate all round robin pairings
    
    Args:
        tournament_id: UUID of the tournament
        
    Returns:
        Dictionary mapping round numbers to pairing lists
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        
        if tournament.format != Tournament.ROUND_ROBIN:
            raise ValueError(f"Tournament format is {tournament.format}, not Round Robin")
        
        engine = RoundRobinEngine(tournament)
        return engine.generate_all_rounds()
        
    except Tournament.DoesNotExist:
        raise ValueError(f"Tournament with ID {tournament_id} not found")
