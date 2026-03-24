from rest_framework import serializers
from .models import MatchmakingQueue


class MatchmakingQueueSerializer(serializers.ModelSerializer):
    """
    Serializer para devolver estado do matchmaking.
    """

    user = serializers.StringRelatedField()

    class Meta:
        model = MatchmakingQueue
        fields = ["id", "user", "joined_at", "preferred_color", "is_guest"]
