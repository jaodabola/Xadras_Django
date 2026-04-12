# XADRAS - Modelos de Torneio
# Implementação baseada nas especificações da Tournament AI
# Prioridade: CRÍTICA - Requerido por 8+ AIs

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import json

User = get_user_model()


class Tournament(models.Model):
    """
    Modelo principal de torneio suportando múltiplos formatos
    Baseado nas especificações da Tournament AI
    """
    # Formatos de Torneio
    SWISS = 'SWISS'
    SINGLE_ELIMINATION = 'SINGLE_ELIMINATION'
    ROUND_ROBIN = 'ROUND_ROBIN'

    FORMAT_CHOICES = [
        (SWISS, 'Swiss System'),
        (SINGLE_ELIMINATION, 'Single Elimination'),
        (ROUND_ROBIN, 'Round Robin'),
    ]

    # Estado do Torneio
    REGISTRATION = 'REGISTRATION'
    IN_PROGRESS = 'IN_PROGRESS'
    FINISHED = 'FINISHED'
    CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (REGISTRATION, 'Registration Open'),
        (IN_PROGRESS, 'In Progress'),
        (FINISHED, 'Finished'),
        (CANCELLED, 'Cancelled'),
    ]

    # Informações Básicas
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Tournament name")
    description = models.TextField(
        blank=True, help_text="Tournament description")

    # Configuração do Torneio
    tournament_type = models.CharField(
        max_length=20, choices=FORMAT_CHOICES, default=SWISS)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=REGISTRATION)
    max_participants = models.IntegerField(
        validators=[MinValueValidator(2), MaxValueValidator(256)],
        default=16,
        help_text="Maximum number of participants"
    )

    # Controlo de Acesso
    join_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique code for joining tournament"
    )
    is_public = models.BooleanField(
        default=True, help_text="Public tournaments appear in listings")
    vision_enabled = models.BooleanField(
        default=False, help_text="Enable physical board tracking integration")

    # Gestão
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tournaments',
        help_text="Tournament organizer"
    )

    # Agendamento
    registration_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Deadline for registration"
    )
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Tournament start time"
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Tournament end time"
    )

    # Progresso do Torneio
    current_round = models.IntegerField(
        default=0, help_text="Current round number")
    total_rounds = models.IntegerField(
        null=True,
        blank=True,
        help_text="Total planned rounds (calculated for some formats)"
    )

    # Controlo de Tempo
    time_control = models.CharField(
        max_length=50,
        default="10+0",
        help_text="Time control string (e.g. 10+0)"
    )
    increment = models.IntegerField(
        default=0,
        help_text="Increment added per move (seconds)"
    )

    # Datas de Registo
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Tournament'
        verbose_name_plural = 'Tournaments'
        indexes = [
            models.Index(fields=['status', 'is_public']),
            models.Index(fields=['join_code']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_tournament_type_display()})"

    def save(self, *args, **kwargs):
        # Gerar código de adesão se não for fornecido
        if not self.join_code:
            self.join_code = self.generate_join_code()
        super().save(*args, **kwargs)

    def generate_join_code(self):
        """Gerar código de adesão único para o torneio"""
        import random
        import string

        while True:
            code = ''.join(random.choices(
                string.ascii_uppercase + string.digits, k=8))
            if not Tournament.objects.filter(join_code=code).exists():
                return code

    @property
    def participant_count(self):
        """Obter o número atual de participantes"""
        return self.participants.filter(is_active=True).count()

    @property
    def is_full(self):
        """Verificar se o torneio está cheio"""
        return self.participant_count >= self.max_participants

    @property
    def can_start(self):
        """Verificar se o torneio pode começar"""
        return (
            self.status == self.REGISTRATION and
            self.participant_count >= 2 and
            (self.registration_deadline is None or timezone.now()
             >= self.registration_deadline)
        )


class TournamentParticipant(models.Model):
    """
    Participante num torneio com pontuação e seeding
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Dados Específicos do Torneio
    seed = models.IntegerField(
        null=True,
        blank=True,
        help_text="Player seeding (1 = highest seed)"
    )
    initial_rating = models.IntegerField(
        help_text="Player's rating when joining tournament"
    )

    # Pontuação
    score = models.FloatField(
        default=0.0,
        help_text="Tournament points (1 for win, 0.5 for draw, 0 for loss)"
    )
    tiebreak_scores = models.JSONField(
        default=dict,
        help_text="Tiebreaker scores (Buchholz, Sonneborn-Berger, etc.)"
    )

    # Estado
    is_active = models.BooleanField(
        default=True,
        help_text="False if player withdrew from tournament"
    )

    # Datas de Registo
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['tournament', 'user']
        ordering = ['-score', 'seed']
        verbose_name = 'Tournament Participant'
        verbose_name_plural = 'Tournament Participants'
        indexes = [
            models.Index(fields=['tournament', 'is_active']),
            models.Index(fields=['tournament', 'score']),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.tournament.name}"

    def save(self, *args, **kwargs):
        # Definir rating inicial a partir do rating atual do utilizador
        if not self.initial_rating:
            self.initial_rating = getattr(self.user, 'elo_rating', 1200)
        super().save(*args, **kwargs)

    def update_score(self, result):
        """Atualizar pontuação com base no resultado do jogo"""
        if result == 'win':
            self.score += 1.0
        elif result == 'draw':
            self.score += 0.5
        # Derrota adiciona 0 pontos
        self.save()

    def calculate_tiebreakers(self):
        """Calcular pontuações de desempate (Buchholz, Sonneborn-Berger, etc.)"""
        # Isto será implementado com o algoritmo de emparelhamento
        # Por agora, inicializar desempates vazios
        if not self.tiebreak_scores:
            self.tiebreak_scores = {
                'buchholz': 0.0,
                'sonneborn_berger': 0.0,
                'direct_encounter': 0.0
            }
            self.save()


class TournamentRound(models.Model):
    """
    Uma ronda num torneio contendo múltiplos emparelhamentos
    """
    # Estado da Ronda
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (IN_PROGRESS, 'In Progress'),
        (COMPLETED, 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='rounds'
    )
    round_number = models.IntegerField(help_text="Round number (1-based)")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=PENDING)

    # Agendamento
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    # Datas de Registo
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['tournament', 'round_number']
        ordering = ['tournament', 'round_number']
        verbose_name = 'Tournament Round'
        verbose_name_plural = 'Tournament Rounds'
        indexes = [
            models.Index(fields=['tournament', 'round_number']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.tournament.name} - Round {self.round_number}"

    @property
    def pairing_count(self):
        """Obter o número de emparelhamentos nesta ronda"""
        return self.pairings.count()

    @property
    def completed_games(self):
        """Obter o número de jogos concluídos nesta ronda"""
        return self.pairings.filter(game__status='FINISHED').count()

    @property
    def is_complete(self):
        """Verificar se todos os jogos na ronda terminaram"""
        total_pairings = self.pairing_count
        if total_pairings == 0:
            return False
        return self.completed_games == total_pairings


class TournamentPairing(models.Model):
    """
    Um emparelhamento entre dois jogadores numa ronda de torneio
    """
    # Tipos de Resultado
    WHITE_WIN = 'WHITE_WIN'
    BLACK_WIN = 'BLACK_WIN'
    DRAW = 'DRAW'
    BYE = 'BYE'
    FORFEIT_WHITE = 'FORFEIT_WHITE'
    FORFEIT_BLACK = 'FORFEIT_BLACK'

    RESULT_CHOICES = [
        (WHITE_WIN, 'White Wins'),
        (BLACK_WIN, 'Black Wins'),
        (DRAW, 'Draw'),
        (BYE, 'Bye'),
        (FORFEIT_WHITE, 'White Forfeits'),
        (FORFEIT_BLACK, 'Black Forfeits'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    round = models.ForeignKey(
        TournamentRound,
        on_delete=models.CASCADE,
        related_name='pairings'
    )

    # Jogadores
    white_player = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tournament_white_pairings',
        null=True,
        blank=True
    )
    black_player = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tournament_black_pairings',
        null=True,
        blank=True
    )

    # Jogador com Bye (para número ímpar de jogadores)
    bye_player = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tournament_bye_pairings',
        null=True,
        blank=True,
        help_text="Player receiving bye (odd number of participants)"
    )

    # Referência ao Jogo
    game = models.OneToOneField(
        'game.Game',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tournament_pairing',
        help_text="Associated game (if not a bye)"
    )

    # Resultados
    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
        null=True,
        blank=True
    )

    # Atribuição de Tabuleiro (para torneios físicos)
    board_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Physical board number for camera assignment"
    )

    # Campos de Integração com IA de Visão (Migração 0005)
    physical_board_id = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Physical board identifier for Vision AI (e.g., 'A1', 'B2')"
    )
    camera_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Camera ID for Vision AI integration"
    )

    # Datas de Registo
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['round', 'board_number']
        verbose_name = 'Tournament Pairing'
        verbose_name_plural = 'Tournament Pairings'
        indexes = [
            models.Index(fields=['round']),
            models.Index(fields=['white_player']),
            models.Index(fields=['black_player']),
            models.Index(fields=['game']),
        ]

    def __str__(self):
        if self.bye_player:
            return f"Round {self.round.round_number}: {self.bye_player.username} (BYE)"
        elif self.white_player and self.black_player:
            return f"Round {self.round.round_number}: {self.white_player.username} vs {self.black_player.username}"
        else:
            return f"Round {self.round.round_number}: Incomplete pairing"

    @property
    def is_bye(self):
        """Verificar se este é um emparelhamento de bye"""
        return self.bye_player is not None

    @property
    def tournament(self):
        """Obter o torneio ao qual este emparelhamento pertence"""
        return self.round.tournament

    def update_result_from_game(self):
        """Atualizar o resultado do emparelhamento com base no resultado do jogo associado"""
        if self.game and self.game.result:
            if self.game.result == 'WHITE_WIN':
                self.result = self.WHITE_WIN
            elif self.game.result == 'BLACK_WIN':
                self.result = self.BLACK_WIN
            elif self.game.result == 'DRAW':
                self.result = self.DRAW
            self.save()

            # Atualizar pontuações dos participantes
            self._update_participant_scores()

    def _update_participant_scores(self):
        """Atualizar as pontuações dos participantes do torneio com base no resultado"""
        if not self.result:
            return

        tournament = self.tournament

        if self.result == self.BYE and self.bye_player:
            # Bye dá 1 ponto
            try:
                participant = TournamentParticipant.objects.get(
                    tournament=tournament,
                    user=self.bye_player
                )
                participant.update_score('win')
            except TournamentParticipant.DoesNotExist:
                pass

        elif self.white_player and self.black_player:
            try:
                white_participant = TournamentParticipant.objects.get(
                    tournament=tournament,
                    user=self.white_player
                )
                black_participant = TournamentParticipant.objects.get(
                    tournament=tournament,
                    user=self.black_player
                )

                if self.result == self.WHITE_WIN:
                    white_participant.update_score('win')
                    black_participant.update_score('loss')
                elif self.result == self.BLACK_WIN:
                    white_participant.update_score('loss')
                    black_participant.update_score('win')
                elif self.result == self.DRAW:
                    white_participant.update_score('draw')
                    black_participant.update_score('draw')

            except TournamentParticipant.DoesNotExist:
                pass

    def to_dict(self):
        """Converter emparelhamento para dicionário para respostas da API"""
        return {
            'id': str(self.id),
            'tournament_id': str(self.round.tournament.id),
            'round_number': self.round.round_number,
            'white_player': {
                'id': self.white_player.id,
                'username': self.white_player.username
            } if self.white_player else None,
            'black_player': {
                'id': self.black_player.id,
                'username': self.black_player.username
            } if self.black_player else None,
            'bye_player': {
                'id': self.bye_player.id,
                'username': self.bye_player.username
            } if self.bye_player else None,
            'is_bye': self.is_bye,
            'board_number': self.board_number,
            'physical_board_id': self.physical_board_id,  # Integração IA de Visão
            'camera_id': self.camera_id,  # Integração IA de Visão
            'result': self.result,
            'game_id': str(self.game.id) if self.game else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
