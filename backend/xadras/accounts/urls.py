from django.urls import path
from .views import GuestView, UserProfileView, UserStatsView, CSRFTokenView, GuestDeleteView

urlpatterns = [
    path('guest/', GuestView.as_view(), name='create_guest'),
    path('guest/delete/', GuestDeleteView.as_view(), name='delete_guest'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('stats/', UserStatsView.as_view(), name='user_stats'),
    path('csrf/', CSRFTokenView.as_view(), name='csrf'),
]
