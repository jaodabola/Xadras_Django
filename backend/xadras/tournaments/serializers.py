# XADRAS - Serializers de Torneio
# Implementação para os endpoints da API de Torneio

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Tournament, TournamentParticipant, TournamentRound, TournamentPairing

User = get_user_model()


class TournamentSerializer(serializers.ModelSerializer):
    """Serializer para o modelo Tournament"""

    participant_count = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    can_start = serializers.ReadOnlyField()
    created_by_username = serializers.CharField(
        source='created_by.username', read_only=True)
    pairings = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = [
            'id', 'name', 'description', 'tournament_type', 'status',
            'max_participants', 'participant_count', 'is_full',
            'join_code', 'is_public', 'vision_enabled', 'created_by', 'created_by_username',
            'registration_deadline', 'start_date', 'end_time',
            'current_round', 'total_rounds', 'time_control', 'increment',
            'can_start', 'created_at', 'updated_at', 'pairings'
        ]
        read_only_fields = ['id', 'join_code',
                            'created_by', 'created_at', 'updated_at']

    def get_pairings(self, obj):
        if obj.status == 'REGISTRATION' or obj.current_round == 0:
            return []
        round_obj = obj.rounds.filter(round_number=obj.current_round).first()
        if round_obj:
            return [p.to_dict() for p in round_obj.pairings.all()]
        return []

    def create(self, validated_data):
        """Criar torneio com o utilizador atual como organizador"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TournamentParticipantSerializer(serializers.ModelSerializer):
    """Serializer para Participante de Torneio"""

    username = serializers.CharField(source='user.username', read_only=True)
    user_rating = serializers.IntegerField(
        source='user.elo_rating', read_only=True)

    class Meta:
        model = TournamentParticipant
        fields = [
            'id', 'tournament', 'user', 'username', 'user_rating',
            'seed', 'initial_rating', 'score', 'tiebreak_scores',
            'is_active', 'joined_at'
        ]
        read_only_fields = ['id', 'initial_rating', 'joined_at']


class TournamentRoundSerializer(serializers.ModelSerializer):
    """Serializer para Ronda de Torneio"""

    pairing_count = serializers.ReadOnlyField()
    completed_games = serializers.ReadOnlyField()
    is_complete = serializers.ReadOnlyField()

    class Meta:
        model = TournamentRound
        fields = [
            'id', 'tournament', 'round_number', 'status',
            'start_time', 'end_time', 'pairing_count',
            'completed_games', 'is_complete',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TournamentPairingSerializer(serializers.ModelSerializer):
    """Serializer para Emparelhamento de Torneio"""

    white_player_username = serializers.CharField(
        source='white_player.username', read_only=True)
    black_player_username = serializers.CharField(
        source='black_player.username', read_only=True)
    bye_player_username = serializers.CharField(
        source='bye_player.username', read_only=True)
    round_number = serializers.IntegerField(
        source='round.round_number', read_only=True)
    tournament_name = serializers.CharField(
        source='round.tournament.name', read_only=True)
    game = serializers.PrimaryKeyRelatedField(read_only=True)
    game_status = serializers.CharField(
        source='game.status', read_only=True)
    is_bye = serializers.ReadOnlyField()

    class Meta:
        model = TournamentPairing
        fields = [
            'id', 'round', 'round_number', 'tournament_name',
            'white_player', 'white_player_username',
            'black_player', 'black_player_username',
            'bye_player', 'bye_player_username',
            'game', 'game_status', 'result', 'board_number', 'is_bye',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TournamentStandingsSerializer(serializers.Serializer):
    """Serializer para a classificação do torneio"""

    position = serializers.IntegerField()
    participant_id = serializers.UUIDField()
    player_id = serializers.CharField()
    player_name = serializers.CharField()
    score = serializers.FloatField()
    games_played = serializers.IntegerField()
    wins = serializers.IntegerField()
    draws = serializers.IntegerField()
    losses = serializers.IntegerField()
    buchholz_score = serializers.FloatField()
    sonneborn_berger_score = serializers.FloatField()
    direct_encounter_score = serializers.FloatField()
    initial_rating = serializers.IntegerField()
    seed = serializers.IntegerField(allow_null=True, required=False)


class TournamentCreateSerializer(serializers.ModelSerializer):
    """Serializer simplificado para a criação de torneios"""

    class Meta:
        model = Tournament
        fields = [
            'name', 'description', 'tournament_type', 'max_participants',
            'is_public', 'vision_enabled', 'registration_deadline', 'start_date', 'time_control', 'increment'
        ]

    def create(self, validated_data):
        """Criar torneio com o utilizador atual como organizador"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TournamentJoinSerializer(serializers.Serializer):
    """Serializer para aderir ao torneio via código de adesão"""

    join_code = serializers.CharField(max_length=20)

    def validate_join_code(self, value):
        """Validar que o código de adesão existe e o torneio permite inscrições"""
        try:
            tournament = Tournament.objects.get(join_code=value.upper())
        except Tournament.DoesNotExist:
            raise serializers.ValidationError("Código de adesão inválido")

        if tournament.status != Tournament.REGISTRATION:
            raise serializers.ValidationError(
                "As inscrições no torneio estão fechadas")

        if tournament.is_full:
            raise serializers.ValidationError("O torneio está cheio")

        return value
