from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/game/(?P<label>[a-z0-9_-]+)/$', consumers.QuizbowlConsumer.as_asgi()),
    re_path(r'ws/game/evaluation/(?P<label>[a-z0-9_-]+)/$', consumers.QuizbowlConsumer.as_asgi()),
]