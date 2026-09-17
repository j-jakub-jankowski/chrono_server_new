from django.urls import re_path

from .web_socket import consumers

websocket_urlpatterns = [
    re_path(r"ws/point_export/(?P<point_id>\w+)/$", consumers.PointConsumer.as_asgi()),
]
