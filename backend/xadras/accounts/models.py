from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Modelo de utilizador personalizado que estende o AbstractUser do Django.

    Inclui estatísticas relacionadas com partidas de xadrez e sistema de rating ELO.
    """

    # Rating ELO inicial do jogador
    elo_rating = models.IntegerField(default=1200)

    # Estatísticas de partidas
    games_played = models.PositiveIntegerField(default=0)
    games_won = models.PositiveIntegerField(default=0)
    games_lost = models.PositiveIntegerField(default=0)
    games_drawn = models.PositiveIntegerField(default=0)

    # Indica se o utilizador é um convidado temporário
    is_guest = models.BooleanField(default=False)

    # Imagem de perfil do utilizador (Avatar)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    # Constante utilizada no cálculo do ELO
    ELO_K_FACTOR = 32

    # Override do related_name para evitar conflitos em projetos com múltiplos modelos de utilizador
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="chess_users",
        blank=True,
        help_text="Grupos aos quais o utilizador pertence.",
        verbose_name="groups",
    )

    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="chess_users",
        blank=True,
        help_text="Permissões específicas atribuídas ao utilizador.",
        verbose_name="user permissions",
    )

    def update_statistics(self, result):
        """
        Atualiza as estatísticas do jogador após uma partida.

        Args:
            result (str): Resultado da partida ('win', 'loss', 'draw')
        """

        valid_results = ["win", "loss", "draw"]

        if result not in valid_results:
            raise ValueError(
                "Resultado inválido. Deve ser 'win', 'loss' ou 'draw'.")

        self.games_played += 1

        if result == "win":
            self.games_won += 1

        elif result == "loss":
            self.games_lost += 1

        elif result == "draw":
            self.games_drawn += 1

    def calculate_elo(self, opponent_rating, result):
        """
        Calcula o novo rating ELO após uma partida.

        Args:
            opponent_rating (int): Rating do adversário
            result (str): Resultado da partida ('win', 'loss', 'draw')

        Returns:
            int: Novo rating ELO calculado
        """

        expected_score = 1 / (
            1 + 10 ** ((opponent_rating - self.elo_rating) / 400)
        )

        if result == "win":
            actual_score = 1
        elif result == "loss":
            actual_score = 0
        elif result == "draw":
            actual_score = 0.5
        else:
            raise ValueError("Resultado inválido.")

        new_rating = self.elo_rating + self.ELO_K_FACTOR * \
            (actual_score - expected_score)

        return round(new_rating)

    def get_win_rate(self):
        """
        Calcula a percentagem de vitórias do jogador.
        """

        if self.games_played == 0:
            return 0

        return round((self.games_won / self.games_played) * 100, 2)

    def get_draw_rate(self):
        """
        Calcula a percentagem de empates do jogador.
        """

        if self.games_played == 0:
            return 0

        return round((self.games_drawn / self.games_played) * 100, 2)

    class Meta:
        ordering = ["-elo_rating"]
        verbose_name = "Utilizador"
        verbose_name_plural = "Utilizadores"
