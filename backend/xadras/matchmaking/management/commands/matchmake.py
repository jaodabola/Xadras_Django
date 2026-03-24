import json
import logging
import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from matchmaking.models import MatchmakingQueue
from game.models import Game

# Set up logging
logger = logging.getLogger('matchmaking.command')
User = get_user_model()

class Command(BaseCommand):
    help = 'Matchmake players in the queue'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            dest='format',
            default='text',
            help='Output format (text/json)',
        )

    def handle(self, *args, **options):
        output_format = options.get('format', 'text')
        response = {}
        
        try:
            # Get all players in queue with related user data
            queue = MatchmakingQueue.objects.select_related('user').all()
            
            logger.info(
                "Starting matchmaking",
                extra={
                    'event': 'matchmaking_start',
                    'queue_size': len(queue),
                    'format': output_format
                }
            )
            
            if len(queue) < 2:
                msg = 'Not enough players in queue (need at least 2)'
                logger.info(msg, extra={'event': 'not_enough_players'})
                
                if output_format == 'json':
                    response = {'status': 'queued', 'message': msg, 'matches': []}
                    self.stdout.write(json.dumps(response))
                else:
                    self.stdout.write(self.style.WARNING(msg))
                return

            # Group players by color preference
            white_players = [p for p in queue if p.preferred_color in ['WHITE', 'ANY']]
            black_players = [p for p in queue if p.preferred_color in ['BLACK', 'ANY']]

            logger.debug(
                "Player counts",
                extra={
                    'event': 'player_counts',
                    'white_players': len(white_players),
                    'black_players': len(black_players),
                    'queue_size': len(queue)
                }
            )

            # Match players
            matched = []
            matches_made = 0
            
            while white_players and black_players and matches_made < 10:  # Limit matches per run
                white_player = random.choice(white_players)
                black_player = random.choice(black_players)
                
                # Skip if players are the same user
                if white_player.user == black_player.user:
                    white_players.remove(white_player)
                    continue

                # Create game
                try:
                    with transaction.atomic():
                        game = Game.objects.create(
                            white_player=white_player.user,
                            black_player=black_player.user,
                            status='IN_PROGRESS'
                        )
                        
                        # Log the match
                        match_info = {
                            'game_id': str(game.id),
                            'white_player': white_player.user.username,
                            'black_player': black_player.user.username,
                            'white_player_id': white_player.user.id,
                            'black_player_id': black_player.user.id,
                            'timestamp': game.created_at.isoformat()
                        }
                        
                        logger.info(
                            "Match created",
                            extra={
                                'event': 'match_created',
                                **match_info
                            }
                        )
                        
                        # Remove players from queue
                        MatchmakingQueue.objects.filter(pk=white_player.pk).delete()
                        MatchmakingQueue.objects.filter(pk=black_player.pk).delete()
                        
                        matched.append(match_info)
                        matches_made += 1
                        
                        # Remove matched players from the queue lists to prevent repeat pairing
                        queue = [p for p in queue if p.pk not in [white_player.pk, black_player.pk]]
                        white_players = [p for p in white_players if p.pk != white_player.pk]
                        black_players = [p for p in black_players if p.pk != black_player.pk]
                        
                except Exception as e:
                    logger.error(
                        "Error creating match",
                        extra={
                            'event': 'match_creation_error',
                            'white_player': white_player.user.username,
                            'black_player': black_player.user.username,
                            'error': str(e),
                            'exception_type': type(e).__name__
                        },
                        exc_info=True
                    )
                    # Continue with next possible match
                    white_players.remove(white_player)
                    continue

            # Prepare response
            if matched:
                msg = f'Successfully matched {len(matched)} games'
                logger.info(msg, extra={'event': 'matchmaking_complete', 'matches_made': len(matched)})
                
                if output_format == 'json':
                    response = {
                        'status': 'success',
                        'message': msg,
                        'matches': matched,
                        'matches_made': len(matched)
                    }
                else:
                    self.stdout.write(self.style.SUCCESS(msg))
                    for i, match in enumerate(matched, 1):
                        self.stdout.write(
                            f"{i}. {match['white_player']} (White) vs {match['black_player']} (Black) - Game ID: {match['game_id']}"
                        )
            else:
                msg = 'No matches found in current queue'
                logger.debug(msg, extra={'event': 'no_matches'})
                
                if output_format == 'json':
                    response = {'status': 'queued', 'message': msg, 'matches': []}
                else:
                    self.stdout.write(self.style.WARNING(msg))
                    
        except Exception as e:
            error_msg = f'Error during matchmaking: {str(e)}'
            logger.error(
                error_msg,
                extra={
                    'event': 'matchmaking_error',
                    'error': str(e),
                    'exception_type': type(e).__name__
                },
                exc_info=True
            )
            
            if output_format == 'json':
                response = {
                    'status': 'error',
                    'message': error_msg,
                    'error': str(e),
                    'exception_type': type(e).__name__
                }
            else:
                self.stderr.write(self.style.ERROR(error_msg))
        
        # Output the response in the requested format
        if output_format == 'json':
            self.stdout.write(json.dumps(response, indent=2))
