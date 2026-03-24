from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GameViewSet
from .live_board_views import LiveBoardFenView

router = DefaultRouter()
router.register(r'', GameViewSet, basename='game')

urlpatterns = [
    # Endpoint para receber FEN de uma app externa (telemóvel)
    path('live-board/fen/', LiveBoardFenView.as_view(), name='live-board-fen'),
    path('', include(router.urls)),
]
