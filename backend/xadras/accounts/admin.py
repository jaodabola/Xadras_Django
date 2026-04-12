# XADRAS - Administração de Contas
from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'elo_rating', 'games_played', 'games_won', 'games_lost', 'games_drawn', 'is_guest')
    list_filter = ('is_guest',)
    search_fields = ('username',)
    ordering = ('-elo_rating',)
