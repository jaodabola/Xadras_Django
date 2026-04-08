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
    white_player = UserSerializer()
    black_player = UserSerializer()
    moves = MoveSerializer(many=True, read_only=True)

    class Meta:
        model = Game
        fields = ['id', 'white_player', 'black_player', 'status', 'result',
                  'time_control', 'created_at', 'updated_at', 'fen_string', 'moves']
