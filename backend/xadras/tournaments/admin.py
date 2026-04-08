# XADRAS - Tournament Admin
# Django admin configuration for tournament models

from django.contrib import admin
from .models import Tournament, TournamentParticipant, TournamentRound, TournamentPairing


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'tournament_type', 'status', 'participant_count',
        'max_participants', 'created_by', 'created_at'
    ]
    list_filter = ['tournament_type', 'status', 'is_public', 'created_at']
    search_fields = ['name', 'join_code', 'created_by__username']
    readonly_fields = ['id', 'join_code',
                       'participant_count', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'tournament_type', 'status')
        }),
        ('Configuration', {
            'fields': ('max_participants', 'is_public', 'vision_enabled', 'join_code', 'time_control', 'increment')
        }),
        ('Management', {
            'fields': ('created_by', 'current_round', 'total_rounds')
        }),
        ('Timing', {
            'fields': ('registration_deadline', 'start_date', 'end_time')
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(TournamentParticipant)
class TournamentParticipantAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'tournament', 'seed', 'score',
        'initial_rating', 'is_active', 'joined_at'
    ]
    list_filter = ['tournament', 'is_active', 'joined_at']
    search_fields = ['user__username', 'tournament__name']
    readonly_fields = ['id', 'initial_rating', 'joined_at']

    fieldsets = (
        ('Participant', {
            'fields': ('tournament', 'user', 'is_active')
        }),
        ('Tournament Data', {
            'fields': ('seed', 'initial_rating', 'score', 'tiebreak_scores')
        }),
        ('System', {
            'fields': ('id', 'joined_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(TournamentRound)
class TournamentRoundAdmin(admin.ModelAdmin):
    list_display = [
        'tournament', 'round_number', 'status',
        'pairing_count', 'completed_games', 'start_time'
    ]
    list_filter = ['status', 'tournament']
    search_fields = ['tournament__name']
    readonly_fields = ['id', 'pairing_count', 'completed_games',
                       'is_complete', 'created_at', 'updated_at']


@admin.register(TournamentPairing)
class TournamentPairingAdmin(admin.ModelAdmin):
    list_display = [
        'round', 'board_number', 'white_player', 'black_player',
        'bye_player', 'result', 'game'
    ]
    list_filter = ['round__tournament', 'result', 'round__round_number']
    search_fields = [
        'white_player__username', 'black_player__username',
        'bye_player__username', 'round__tournament__name'
    ]
    readonly_fields = ['id', 'is_bye',
                       'tournament', 'created_at', 'updated_at']

    def tournament(self, obj):
        return obj.round.tournament.name
    tournament.short_description = 'Tournament'
