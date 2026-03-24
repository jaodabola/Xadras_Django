from django.contrib import admin
from .models import MatchmakingQueue


@admin.register(MatchmakingQueue)
class MatchmakingQueueAdmin(admin.ModelAdmin):
    """Admin para visualizar jogadores na fila de matchmaking"""

    list_display = ("user", "joined_at", "rating",
                    "preferred_color", "is_guest")
    list_filter = ("preferred_color", "is_guest")
    search_fields = ("user__username",)
    ordering = ("-joined_at",)
    readonly_fields = ("joined_at",)
