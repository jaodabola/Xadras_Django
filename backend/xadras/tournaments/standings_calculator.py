# XADRAS - Tournament Standings Calculator
# Implementation by Tournament Logic AI
# Priority: CRITICAL - Tiebreakers (Buchholz, Sonneborn-Berger, Direct Encounter)

from django.db import models
from django.contrib.auth import get_user_model
from .models import Tournament, TournamentParticipant, TournamentPairing
from typing import List, Dict, Tuple
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class TournamentStandingsCalculator:
    """
    Calculate tournament standings with comprehensive tiebreaker system
    
    Tiebreakers implemented:
    1. Buchholz Score (sum of opponents' scores)
    2. Sonneborn-Berger Score (sum of defeated opponents' scores + half of drawn opponents' scores)
    3. Direct Encounter (head-to-head results between tied players)
    4. Number of wins
    5. Initial rating (highest breaks tie)
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
        
        # Cache for performance
        self._opponent_cache = {}
        self._result_cache = {}
        
    def calculate_standings(self) -> List[Dict]:
        """
        Calculate complete tournament standings with all tiebreakers
        
        Returns:
            List of participant standings ordered by rank
        """
        logger.info(f"Calculating standings for tournament {self.tournament.name}")
        
        standings = []
        
        for participant in self.participants:
            standing = self._calculate_participant_standing(participant)
            standings.append(standing)
        
        # Sort by all tiebreaker criteria
        standings.sort(key=lambda x: (
            -x['score'],                    # Primary: highest score
            -x['buchholz_score'],          # 1st tiebreaker: Buchholz
            -x['sonneborn_berger_score'],  # 2nd tiebreaker: Sonneborn-Berger
            -x['direct_encounter_score'],   # 3rd tiebreaker: Direct encounter
            -x['wins'],                     # 4th tiebreaker: Most wins
            -x['initial_rating']            # 5th tiebreaker: Highest initial rating
        ))
        
        # Assign positions
        for i, standing in enumerate(standings, 1):
            standing['position'] = i
        
        # Update participant tiebreak scores in database
        self._update_tiebreak_scores(standings)
        
        logger.info(f"Calculated standings for {len(standings)} participants")
        return standings
    
    def _calculate_participant_standing(self, participant: TournamentParticipant) -> Dict:
        """Calculate complete standing information for a participant"""
        user = participant.user
        
        # Get basic game statistics
        games_played, wins, draws, losses = self._get_game_statistics(user)
        
        # Calculate tiebreaker scores
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
            'position': 0  # Will be set after sorting
        }
    
    def _get_game_statistics(self, user: User) -> Tuple[int, int, int, int]:
        """
        Get basic game statistics for a user
        
        Returns:
            Tuple of (games_played, wins, draws, losses)
        """
        if user.id in self._result_cache:
            return self._result_cache[user.id]
        
        wins = draws = losses = 0
        
        for pairing in self.pairings:
            if pairing.bye_player == user:
                # Bye counts as a win
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
        Calculate Buchholz score (sum of opponents' scores)
        
        The Buchholz score is the sum of the scores of all opponents
        a player has faced in the tournament.
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
                # Opponent not found (shouldn't happen), skip
                continue
        
        return buchholz_score
    
    def _calculate_sonneborn_berger_score(self, user: User) -> float:
        """
        Calculate Sonneborn-Berger score
        
        The Sonneborn-Berger score is the sum of:
        - Full scores of defeated opponents
        - Half scores of drawn opponents
        - Zero for opponents who defeated this player
        """
        sonneborn_berger_score = 0.0
        
        for pairing in self.pairings:
            opponent = None
            result_for_user = None
            
            if pairing.bye_player == user:
                # Bye doesn't contribute to Sonneborn-Berger
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
                        # Add full score of defeated opponent
                        sonneborn_berger_score += opponent_participant.score
                    elif result_for_user == 'draw':
                        # Add half score of drawn opponent
                        sonneborn_berger_score += opponent_participant.score * 0.5
                    # For losses, add nothing
                    
                except TournamentParticipant.DoesNotExist:
                    continue
        
        return sonneborn_berger_score
    
    def _calculate_direct_encounter_score(self, user: User) -> float:
        """
        Calculate direct encounter score
        
        This is used when comparing players with the same score.
        Returns the score achieved in games directly between tied players.
        
        Note: This is a simplified version. Full implementation would
        require knowing which specific players are tied.
        """
        # For now, return 0. This would be calculated when resolving
        # ties between specific players
        return 0.0
    
    def _get_opponents(self, user: User) -> List[User]:
        """Get list of all opponents a user has faced"""
        if user.id in self._opponent_cache:
            return self._opponent_cache[user.id]
        
        opponents = []
        
        for pairing in self.pairings:
            if pairing.bye_player == user:
                # Bye has no opponent
                continue
            elif pairing.white_player == user and pairing.black_player:
                opponents.append(pairing.black_player)
            elif pairing.black_player == user and pairing.white_player:
                opponents.append(pairing.white_player)
        
        self._opponent_cache[user.id] = opponents
        return opponents
    
    def _update_tiebreak_scores(self, standings: List[Dict]):
        """Update tiebreak scores in the database"""
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
                logger.warning(f"Participant {standing['participant_id']} not found for tiebreak update")
    
    def calculate_direct_encounter_between_players(self, players: List[User]) -> Dict[int, float]:
        """
        Calculate direct encounter scores between specific tied players
        
        Args:
            players: List of tied players to compare
            
        Returns:
            Dictionary mapping user_id to direct encounter score
        """
        player_ids = {player.id for player in players}
        direct_scores = {player.id: 0.0 for player in players}
        
        # Find all pairings between these specific players
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
    Main function to calculate tournament standings
    
    Args:
        tournament_id: UUID of the tournament
        
    Returns:
        List of standings dictionaries ordered by rank
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        calculator = TournamentStandingsCalculator(tournament)
        return calculator.calculate_standings()
        
    except Tournament.DoesNotExist:
        raise ValueError(f"Tournament with ID {tournament_id} not found")


def update_participant_tiebreakers(tournament_id: str):
    """
    Update tiebreaker scores for all participants in a tournament
    
    Args:
        tournament_id: UUID of the tournament
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        calculator = TournamentStandingsCalculator(tournament)
        
        # Calculate standings (this also updates tiebreakers)
        calculator.calculate_standings()
        
        logger.info(f"Updated tiebreaker scores for tournament {tournament.name}")
        
    except Tournament.DoesNotExist:
        raise ValueError(f"Tournament with ID {tournament_id} not found")
