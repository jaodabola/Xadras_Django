from django.contrib import admin
from .models import Game, Move

from django.utils.html import format_html
from django.urls import reverse

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('id', 'white_player_link', 'black_player_link', 'status', 'result', 'created_at')
    list_filter = ('status', 'result')
    search_fields = ('white_player__username', 'black_player__username')
    ordering = ('-created_at',)

    @admin.display(description='White Player')
    def white_player_link(self, obj):
        if obj.white_player:
            url = reverse('admin:accounts_user_change', args=[obj.white_player.id])
            return format_html('<a href="{}">{}</a>', url, obj.white_player.username)
        return '-'

    @admin.display(description='Black Player')
    def black_player_link(self, obj):
        if obj.black_player:
            url = reverse('admin:accounts_user_change', args=[obj.black_player.id])
            return format_html('<a href="{}">{}</a>', url, obj.black_player.username)
        return '-'

@admin.register(Move)
class MoveAdmin(admin.ModelAdmin):
    list_display = ('game', 'move_number', 'move_san', 'created_at')
    list_filter = ('game',)
    ordering = ('game', 'move_number')
