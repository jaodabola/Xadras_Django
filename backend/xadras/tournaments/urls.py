# XADRAS - URLs de Torneio
# Roteamento de URLs para os endpoints de torneio

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TournamentViewSet, TournamentJoinByCodeView

# Criar router para os endpoints de torneio
router = DefaultRouter()
router.register(r'tournaments', TournamentViewSet, basename='tournament')
router.register(r'join', TournamentJoinByCodeView, basename='tournament-join')

urlpatterns = [
    path('', include(router.urls)),
]
