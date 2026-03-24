import logging
from django.urls import path
from .views import MatchmakingView

logger = logging.getLogger("matchmaking.urls")

logger.info("Loading matchmaking URLs")

urlpatterns = [
    path("", MatchmakingView.as_view(), name="matchmaking"),
]
