# XADRAS - Tournament Serializers
# Implementation for Tournament API endpoints

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Tournament, TournamentParticipant, TournamentRound, TournamentPairing

User = get_user_model()

class TournamentSerializer(serializers.ModelSerializer):
    """Serializer for Tournament model"""
    
    participant_count = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    can_start = serializers.ReadOnlyField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Tournament
        fields = [
            'id', 'name', 'description', 'format', 'status',
            'max_participants', 'participant_count', 'is_full',
            'join_code', 'is_public', 'created_by', 'created_by_username',
            'registration_deadline', 'start_time', 'end_time',
            'current_round', 'total_rounds', 'time_control',
            'can_start', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'join_code', 'created_by', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Create tournament with current user as organizer"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TournamentParticipantSerializer(serializers.ModelSerializer):
    """Serializer for Tournament Participant"""
    
    username = serializers.CharField(source='user.username', read_only=True)
    user_rating = serializers.IntegerField(source='user.elo_rating', read_only=True)
    
    class Meta:
        model = TournamentParticipant
        fields = [
            'id', 'tournament', 'user', 'username', 'user_rating',
            'seed', 'initial_rating', 'score', 'tiebreak_scores',
            'is_active', 'joined_at'
        ]
        read_only_fields = ['id', 'initial_rating', 'joined_at']


class TournamentRoundSerializer(serializers.ModelSerializer):
    """Serializer for Tournament Round"""
    
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
    """Serializer for Tournament Pairing"""
    
    white_player_username = serializers.CharField(source='white_player.username', read_only=True)
    black_player_username = serializers.CharField(source='black_player.username', read_only=True)
    bye_player_username = serializers.CharField(source='bye_player.username', read_only=True)
    round_number = serializers.IntegerField(source='round.round_number', read_only=True)
    tournament_name = serializers.CharField(source='round.tournament.name', read_only=True)
    is_bye = serializers.ReadOnlyField()
    
    class Meta:
        model = TournamentPairing
        fields = [
            'id', 'round', 'round_number', 'tournament_name',
            'white_player', 'white_player_username',
            'black_player', 'black_player_username',
            'bye_player', 'bye_player_username',
            'game', 'result', 'board_number', 'is_bye',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TournamentStandingsSerializer(serializers.Serializer):
    """Serializer for tournament standings"""
    
    position = serializers.IntegerField()
    user_id = serializers.UUIDField()
    username = serializers.CharField()
    score = serializers.FloatField()
    games_played = serializers.IntegerField()
    wins = serializers.IntegerField()
    draws = serializers.IntegerField()
    losses = serializers.IntegerField()
    tiebreak_scores = serializers.JSONField()
    initial_rating = serializers.IntegerField()


class TournamentCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for tournament creation"""
    
    class Meta:
        model = Tournament
        fields = [
            'name', 'description', 'format', 'max_participants',
            'is_public', 'registration_deadline', 'time_control'
        ]
    
    def create(self, validated_data):
        """Create tournament with current user as organizer"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TournamentJoinSerializer(serializers.Serializer):
    """Serializer for joining tournament via join code"""
    
    join_code = serializers.CharField(max_length=20)
    
    def validate_join_code(self, value):
        """Validate that join code exists and tournament is joinable"""
        try:
            tournament = Tournament.objects.get(join_code=value.upper())
        except Tournament.DoesNotExist:
            raise serializers.ValidationError("Invalid join code")
        
        if tournament.status != Tournament.REGISTRATION:
            raise serializers.ValidationError("Tournament registration is closed")
        
        if tournament.is_full:
            raise serializers.ValidationError("Tournament is full")
        
        return value
