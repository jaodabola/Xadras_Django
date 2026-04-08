from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from .models import Game, Move
from .serializers import GameSerializer, MoveSerializer

User = get_user_model()


class GameViewSet(viewsets.ModelViewSet):
    serializer_class = GameSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Game.objects.filter(
            models.Q(white_player=user) | models.Q(black_player=user)
        )

    @method_decorator(ratelimit(key='user', rate='10/m', method='POST', block=True))
    def create(self, request, *args, **kwargs):
        """Create a new game"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create game with current user as white player
        game = Game.objects.create(
            white_player=request.user,
            status='PENDING'
        )

        serializer = self.get_serializer(game)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join an existing game as black player"""
        game = self.get_object()
        if game.black_player or game.status != 'PENDING':
            return Response({'error': 'Game is not available'}, status=status.HTTP_400_BAD_REQUEST)

        game.black_player = request.user
        game.status = 'IN_PROGRESS'
        game.save()

        serializer = self.get_serializer(game)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @method_decorator(ratelimit(key='user', rate='60/m', method='POST', block=False))
    def move(self, request, pk=None):
        """Make a move in the game with improved validation and atomic operations"""
        from django.db import transaction
        import chess
        import logging

        logger = logging.getLogger(__name__)

        game = self.get_object()

        # Validate game status
        if game.status != 'IN_PROGRESS':
            return Response({'error': 'Game is not in progress'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate required move data
        move_san = request.data.get('move_san')
        fen_after = request.data.get('fen_after')

        if not move_san or not fen_after:
            return Response({'error': 'Missing move data (move_san and fen_after required)'}, status=status.HTTP_400_BAD_REQUEST)

        # Use atomic transaction to prevent race conditions
        try:
            with transaction.atomic():
                # Get locked game row to prevent race conditions
                game_locked = Game.objects.select_for_update().get(id=game.id)

                # Determine whose turn it is from the current game FEN string
                try:
                    board_before = chess.Board(game_locked.fen_string)
                except ValueError:
                    return Response({'error': 'Invalid game FEN state on server'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                is_white_turn = board_before.turn == chess.WHITE

                # Current move count is still used only for numbering
                current_move_count = Move.objects.filter(
                    game=game_locked).count()

                # Validate turn ownership
                if is_white_turn and game_locked.white_player != request.user:
                    return Response({'error': 'Not your turn - it is white\'s turn'}, status=status.HTTP_400_BAD_REQUEST)
                elif not is_white_turn and game_locked.black_player != request.user:
                    return Response({'error': 'Not your turn - it is black\'s turn'}, status=status.HTTP_400_BAD_REQUEST)

                # Validate FEN string format
                try:
                    chess_board = chess.Board(fen_after)
                except ValueError:
                    return Response({'error': 'Invalid FEN string format'}, status=status.HTTP_400_BAD_REQUEST)

                # Create move with reliable move numbering
                move_number = current_move_count + 1
                move = Move.objects.create(
                    game=game_locked,
                    move_number=move_number,
                    move_san=move_san,
                    fen_after=fen_after
                )

                # Update game FEN to match the latest move
                game_locked.fen_string = fen_after
                game_locked.save()

                # Check for game end conditions
                if chess_board.is_checkmate():
                    game_locked.status = 'FINISHED'
                    # Black won (white is in checkmate)
                    if chess_board.turn == chess.WHITE:
                        game_locked.result = 'BLACK_WIN'
                    else:  # White won (black is in checkmate)
                        game_locked.result = 'WHITE_WIN'
                    game_locked.save()
                elif chess_board.is_stalemate() or chess_board.is_insufficient_material():
                    game_locked.status = 'FINISHED'
                    game_locked.result = 'DRAW'
                    game_locked.save()

                serializer = MoveSerializer(move)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f'Failed to save move: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """End the game with a result"""
        game = self.get_object()

        if game.status != 'IN_PROGRESS':
            return Response({'error': 'Game is not in progress'}, status=status.HTTP_400_BAD_REQUEST)

        result = request.data.get('result')
        if result not in ['WHITE_WIN', 'BLACK_WIN', 'DRAW']:
            return Response({'error': 'Invalid result'}, status=status.HTTP_400_BAD_REQUEST)

        # Update game result and status
        game.result = result
        game.status = 'FINISHED'
        game.save()

        # Update player statistics
        if result == 'WHITE_WIN':
            game.white_player.update_statistics('win')
            game.black_player.update_statistics('loss')
        elif result == 'BLACK_WIN':
            game.white_player.update_statistics('loss')
            game.black_player.update_statistics('win')
        else:  # DRAW
            game.white_player.update_statistics('draw')
            game.black_player.update_statistics('draw')

        # Calculate new ELO ratings
        white_win_status = 'win' if result == 'WHITE_WIN' else 'loss' if result == 'BLACK_WIN' else 'draw'
        black_win_status = 'win' if result == 'BLACK_WIN' else 'loss' if result == 'WHITE_WIN' else 'draw'

        new_white_elo = game.white_player.calculate_elo(
            game.black_player.elo_rating, white_win_status)
        new_black_elo = game.black_player.calculate_elo(
            game.white_player.elo_rating, black_win_status)

        game.white_player.elo_rating = new_white_elo
        game.black_player.elo_rating = new_black_elo

        # Save updated statistics
        game.white_player.save()
        game.black_player.save()

        serializer = self.get_serializer(game)
        return Response(serializer.data)
