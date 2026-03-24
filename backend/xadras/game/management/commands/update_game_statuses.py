"""
Management command to automatically update game statuses.
Marks games as FINISHED based on certain conditions.
"""
import logging
import sys
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from django.db.models import Q
from game.models import Game

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class Command(BaseCommand):
    help = 'Update game statuses based on game conditions'
    
    def handle(self, *args, **options):
        try:
            from game.models import Game  # Import here to use model constants
            
            self.stdout.write(self.style.SUCCESS('Starting game status update...'))
            logger.info(f'Current time: {timezone.now()}')
            
            # Log database connection info
            logger.info(f'Database: {connection.settings_dict["NAME"]} on {connection.settings_dict["HOST"]}')
            
            # Get counts before updates
            total_games = Game.objects.count()
            in_progress_before = Game.objects.filter(status=Game.IN_PROGRESS).count()
            logger.info(f'Total games: {total_games}')
            logger.info(f'Games in progress before update: {in_progress_before}')
            
            if in_progress_before > 0:
                # Log some example games for debugging
                sample_games = Game.objects.filter(status=Game.IN_PROGRESS)[:3]
                for i, game in enumerate(sample_games, 1):
                    logger.info(f'Sample game {i}: ID={game.id}, Updated={game.updated_at}, FEN={game.fen_string[:50]}...')
            
            # Run updates
            self.update_inactive_games()
            self.update_checkmate_or_draw_games()
            
            # Get counts after updates
            in_progress_after = Game.objects.filter(status=Game.IN_PROGRESS).count()
            logger.info(f'Games in progress after update: {in_progress_after}')
            logger.info(self.style.SUCCESS('Game status update complete'))
            
            # Also output to stdout for Docker logs
            self.stdout.write(self.style.SUCCESS(f'Updated {in_progress_before - in_progress_after} games'))
            
        except Exception as e:
            logger.error(f'Error in update_game_statuses: {str(e)}', exc_info=True)
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))
            raise
    
    def update_inactive_games(self):
        """Mark games as FINISHED if they've been inactive for too long"""
        from game.models import Game  # Import here to avoid circular imports
        
        # Consider games inactive if no move in last 24 hours
        inactive_threshold = timezone.now() - timedelta(hours=24)
        
        # Find games that are IN_PROGRESS but haven't been updated recently
        inactive_games = Game.objects.filter(
            status=Game.IN_PROGRESS,
            updated_at__lt=inactive_threshold
        )
        
        count = inactive_games.count()
        if count > 0:
            inactive_games.update(
                status=Game.FINISHED,
                result=Game.DRAW  # Consider it a draw if both players abandoned
            )
            logger.info(f'Marked {count} inactive games as FINISHED')
            self.stdout.write(self.style.SUCCESS(f'Marked {count} inactive games as FINISHED'))
    
    def update_checkmate_or_draw_games(self):
        """Mark games as FINISHED if they have a checkmate or draw FEN"""
        from game.models import Game  # Import here to avoid circular imports
        
        # These are patterns that typically indicate a finished game
        finished_patterns = [
            '#',  # Checkmate
            '1-0',  # White wins
            '0-1',  # Black wins
            '1/2-1/2',  # Draw
        ]
        
        # Build a query to find games with any of these patterns in their FEN
        query = Q()
        for pattern in finished_patterns:
            query |= Q(fen_string__contains=pattern)
        
        # Find games that appear to be finished but aren't marked as such
        finished_but_not_updated = Game.objects.filter(
            query,
            status=Game.IN_PROGRESS
        )
        
        count = finished_but_not_updated.count()
        if count > 0:
            finished_but_not_updated.update(status=Game.FINISHED)
            logger.info(f'Marked {count} checkmate/draw games as FINISHED')
            self.stdout.write(self.style.SUCCESS(f'Marked {count} checkmate/draw games as FINISHED'))
