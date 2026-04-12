from django.urls import re_path
from . import consumers
from .live_board_consumer import LiveBoardConsumer

websocket_urlpatterns = [
    re_path(r'ws/game/(?P<game_id>\d+)/$', consumers.GameConsumer.as_asgi()),
    re_path(r'ws/live-board/$', LiveBoardConsumer.as_asgi()),
]
