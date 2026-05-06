from rest_framework import serializers
from .models import Game, Move
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'elo_rating', 'games_played',
                  'games_won', 'games_lost', 'games_drawn']


class MoveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Move
        fields = ['id', 'move_number', 'move_san', 'fen_after', 'created_at']


class GameSerializer(serializers.ModelSerializer):
    white_player = UserSerializer(read_only=True)
    black_player = UserSerializer(read_only=True)
    moves = MoveSerializer(many=True, read_only=True)
    move_count = serializers.IntegerField(read_only=True)
    tournament_id = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = ['id', 'white_player', 'black_player', 'status', 'result',
                  'game_type', 'time_control', 'created_at', 'updated_at',
                  'fen_string', 'moves', 'move_count', 'tournament_id']

    def get_tournament_id(self, obj):
        """Retorna o ID do torneio se este jogo pertencer a um emparelhamento de torneio."""
        try:
            pairing = obj.tournament_pairing
            if pairing:
                return str(pairing.round.tournament.id)
        except Exception:
            pass
        return None
