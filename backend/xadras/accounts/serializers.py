from rest_framework import serializers
from django.contrib.auth import get_user_model

from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer


User = get_user_model()


class CustomUserSerializer(BaseUserSerializer):
    """
    Serializer utilizado para representar dados do utilizador.
    Inclui estatísticas relacionadas com partidas de xadrez.
    """

    # Campos calculados dinamicamente
    win_rate = serializers.SerializerMethodField()
    draw_rate = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = (
            "id",
            "username",
            "email",
            "elo_rating",
            "games_played",
            "games_won",
            "games_lost",
            "games_drawn",
            "win_rate",
            "draw_rate",
            "is_guest",
        )

        read_only_fields = (
            "id",
            "elo_rating",
            "games_played",
            "games_won",
            "games_lost",
            "games_drawn",
            "is_guest",
        )

    def get_win_rate(self, obj):
        """
        Calcula a percentagem de vitórias do jogador.
        """

        if obj.games_played == 0:
            return 0

        return round((obj.games_won / obj.games_played) * 100, 2)

    def get_draw_rate(self, obj):
        """
        Calcula a percentagem de empates do jogador.
        """

        if obj.games_played == 0:
            return 0

        return round((obj.games_drawn / obj.games_played) * 100, 2)


class CustomUserCreateSerializer(BaseUserCreateSerializer):
    """
    Serializer responsável pela criação de novos utilizadores.
    Utiliza a implementação base do Djoser com pequenas adaptações.
    """

    class Meta(BaseUserCreateSerializer.Meta):
        model = User

        fields = (
            "id",
            "username",
            "email",
            "password",
        )

        extra_kwargs = {
            "password": {"write_only": True},
            "email": {"required": True},
        }

    def validate_email(self, value):
        """
        Normaliza o email para evitar duplicados com diferentes capitalizações.
        """

        return value.lower()

    def validate(self, attrs):
        """
        Garante que o username é definido automaticamente caso não seja fornecido.
        """

        if not attrs.get("username"):
            attrs["username"] = attrs.get("email")

        return attrs
