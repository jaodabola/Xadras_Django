from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class MatchmakingQueue(models.Model):
    """
    Representa um jogador na fila de matchmaking.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(default=1000)
    joined_at = models.DateTimeField(default=timezone.now)

    preferred_color = models.CharField(
        max_length=5,
        choices=[
            ("WHITE", "White"),
            ("BLACK", "Black"),
            ("ANY", "Any"),
        ],
        default="ANY",
    )

    is_guest = models.BooleanField(default=False)

    class Meta:
        ordering = ["joined_at"]
        verbose_name = "Matchmaking Queue"
        verbose_name_plural = "Matchmaking Queue"

    def __str__(self):
        return f"{self.user.username} (rating: {self.rating})"

    @property
    def position(self):
        """
        Retorna a posição do jogador na fila.
        """
        return MatchmakingQueue.objects.filter(joined_at__lte=self.joined_at).count()
