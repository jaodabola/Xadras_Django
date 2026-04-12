from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Game(models.Model):
    """Modelo para representar um jogo de xadrez"""
    # Constantes de estado
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    FINISHED = 'FINISHED'

    # Constantes de resultado
    WHITE_WIN = 'WHITE_WIN'
    BLACK_WIN = 'BLACK_WIN'
    DRAW = 'DRAW'

    # Constantes de tipo de jogo
    ONLINE = 'ONLINE'
    LIVE_CAPTURE = 'LIVE_CAPTURE'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (IN_PROGRESS, 'In Progress'),
        (FINISHED, 'Finished')
    ]

    RESULT_CHOICES = [
        (WHITE_WIN, 'White Wins'),
        (BLACK_WIN, 'Black Wins'),
        (DRAW, 'Draw')
    ]

    GAME_TYPE_CHOICES = [
        (ONLINE, 'Online'),
        (LIVE_CAPTURE, 'Live Capture'),
    ]

    white_player = models.ForeignKey(
        User, related_name='white_games', on_delete=models.CASCADE)
    black_player = models.ForeignKey(
        User, related_name='black_games', on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='PENDING')
    result = models.CharField(
        max_length=20, choices=RESULT_CHOICES, null=True, blank=True)
    game_type = models.CharField(
        max_length=20, choices=GAME_TYPE_CHOICES, default='ONLINE')
    time_control = models.CharField(
        max_length=20,
        choices=[
            ('bullet', 'Bullet'),
            ('blitz', 'Blitz'),
            ('rapid', 'Rapid'),
            ('classical', 'Classical'),
            ('unlimited', 'Sem Tempo'),
        ],
        default='rapid'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    fen_string = models.TextField(
        default='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Game'
        verbose_name_plural = 'Games'

    def __str__(self):
        return f"Game {self.id}: {self.white_player.username} vs {self.black_player.username if self.black_player else 'Waiting'}"


class Move(models.Model):
    """Modelo para representar uma jogada de xadrez"""
    game = models.ForeignKey(Game, related_name='moves',
                             on_delete=models.CASCADE)
    move_number = models.IntegerField()
    move_san = models.CharField(max_length=10)  # Standard Algebraic Notation
    fen_after = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['move_number']
        verbose_name = 'Move'
        verbose_name_plural = 'Moves'
        indexes = [
            # Recuperação rápida de jogadas do jogo
            models.Index(fields=['game', 'move_number']),
            # Consultas cronológicas
            models.Index(fields=['game', 'created_at']),
            # Jogadas recentes em todos os jogos
            models.Index(fields=['created_at']),
        ]
        # Prevenir números de jogada duplicados
        unique_together = ['game', 'move_number']

    def __str__(self):
        return f"Move {self.move_number}: {self.move_san}"
