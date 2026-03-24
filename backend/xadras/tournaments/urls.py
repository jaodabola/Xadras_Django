# XADRAS - Tournament URLs
# URL routing for tournament endpoints

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TournamentViewSet, TournamentJoinByCodeView

# Create router for tournament endpoints
router = DefaultRouter()
router.register(r'tournaments', TournamentViewSet, basename='tournament')
router.register(r'join', TournamentJoinByCodeView, basename='tournament-join')

urlpatterns = [
    path('', include(router.urls)),
]
