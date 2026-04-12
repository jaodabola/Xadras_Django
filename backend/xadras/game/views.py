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
        """Cria um novo jogo"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Cria o jogo com o utilizador atual como jogador das brancas
        game = Game.objects.create(
            white_player=request.user,
            status='PENDING'
        )

        serializer = self.get_serializer(game)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Entrar num jogo existente como jogador das pretas"""
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
        """Realiza uma jogada no jogo com validação melhorada e operações atómicas"""
        from django.db import transaction
        import chess
        import logging

        logger = logging.getLogger(__name__)

        game = self.get_object()

        # Validar o estado do jogo
        if game.status != 'IN_PROGRESS':
            return Response({'error': 'Game is not in progress'}, status=status.HTTP_400_BAD_REQUEST)

        # Validar dados de jogada obrigatórios
        move_san = request.data.get('move_san')
        fen_after = request.data.get('fen_after')

        if not move_san or not fen_after:
            return Response({'error': 'Missing move data (move_san and fen_after required)'}, status=status.HTTP_400_BAD_REQUEST)

        # Usar transação atómica para prevenir condições de corrida
        try:
            with transaction.atomic():
                # Obter linha do jogo bloqueada para prevenir condições de corrida
                game_locked = Game.objects.select_for_update().get(id=game.id)

                # Determinar de quem é o turno a partir da string FEN atual do jogo
                try:
                    board_before = chess.Board(game_locked.fen_string)
                except ValueError:
                    return Response({'error': 'Invalid game FEN state on server'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                is_white_turn = board_before.turn == chess.WHITE

                # A contagem atual de jogadas ainda é usada apenas para numeração
                current_move_count = Move.objects.filter(
                    game=game_locked).count()

                # Validar a posse do turno
                if is_white_turn and game_locked.white_player != request.user:
                    return Response({'error': 'Not your turn - it is white\'s turn'}, status=status.HTTP_400_BAD_REQUEST)
                elif not is_white_turn and game_locked.black_player != request.user:
                    return Response({'error': 'Not your turn - it is black\'s turn'}, status=status.HTTP_400_BAD_REQUEST)

                # Validar o formato da string FEN
                try:
                    chess_board = chess.Board(fen_after)
                except ValueError:
                    return Response({'error': 'Invalid FEN string format'}, status=status.HTTP_400_BAD_REQUEST)

                # Criar jogada com numeração de jogada fiável
                move_number = current_move_count + 1
                move = Move.objects.create(
                    game=game_locked,
                    move_number=move_number,
                    move_san=move_san,
                    fen_after=fen_after
                )

                # Atualizar o FEN do jogo para corresponder à última jogada
                game_locked.fen_string = fen_after
                game_locked.save()

                # Verificar condições de fim de jogo
                if chess_board.is_checkmate():
                    game_locked.status = 'FINISHED'
                    # Pretas venceram (brancas estão em xeque-mate)
                    if chess_board.turn == chess.WHITE:
                        game_locked.result = 'BLACK_WIN'
                    else:  # Brancas venceram (pretas estão em xeque-mate)
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
        """Terminar o jogo com um resultado"""
        game = self.get_object()

        if game.status != 'IN_PROGRESS':
            return Response({'error': 'Game is not in progress'}, status=status.HTTP_400_BAD_REQUEST)

        result = request.data.get('result')
        if result not in ['WHITE_WIN', 'BLACK_WIN', 'DRAW']:
            return Response({'error': 'Invalid result'}, status=status.HTTP_400_BAD_REQUEST)

        # Atualizar resultado e estado do jogo
        game.result = result
        game.status = 'FINISHED'
        game.save()

        # Atualizar estatísticas dos jogadores
        if result == 'WHITE_WIN':
            game.white_player.update_statistics('win')
            game.black_player.update_statistics('loss')
        elif result == 'BLACK_WIN':
            game.white_player.update_statistics('loss')
            game.black_player.update_statistics('win')
        else:  # DRAW
            game.white_player.update_statistics('draw')
            game.black_player.update_statistics('draw')

        # Calcular novos ratings ELO
        white_win_status = 'win' if result == 'WHITE_WIN' else 'loss' if result == 'BLACK_WIN' else 'draw'
        black_win_status = 'win' if result == 'BLACK_WIN' else 'loss' if result == 'WHITE_WIN' else 'draw'

        new_white_elo = game.white_player.calculate_elo(
            game.black_player.elo_rating, white_win_status)
        new_black_elo = game.black_player.calculate_elo(
            game.white_player.elo_rating, black_win_status)

        game.white_player.elo_rating = new_white_elo
        game.black_player.elo_rating = new_black_elo

        # Guardar estatísticas atualizadas
        game.white_player.save()
        game.black_player.save()

        serializer = self.get_serializer(game)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_games(self, request):
        """Listar todos os jogos do utilizador atual, opcionalmente filtrados por game_type."""
        user = request.user
        game_type = request.query_params.get('game_type')

        queryset = Game.objects.filter(
            models.Q(white_player=user) | models.Q(black_player=user)
        ).order_by('-created_at')

        if game_type:
            queryset = queryset.filter(game_type=game_type)

        # Adicionar contagem de moves via anotação
        queryset = queryset.annotate(move_count=models.Count('moves'))

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def replay(self, request, pk=None):
        """Obter todos os FENs de um jogo para replay."""
        game = self.get_object()

        moves = Move.objects.filter(game=game).order_by('move_number')
        starting_fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

        fens = [starting_fen]
        for move in moves:
            fens.append(move.fen_after)

        return Response({
            'game_id': game.id,
            'game_type': game.game_type,
            'status': game.status,
            'result': game.result,
            'created_at': game.created_at,
            'white_player': game.white_player.username,
            'black_player': game.black_player.username if game.black_player else None,
            'fens': fens,
            'total_moves': moves.count(),
        })
