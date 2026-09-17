from django.urls import include, path


from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("device/all", views.device_all, name="device_all"),
    path("device/<int:device_id>", views.device, name="device"),
    path(
        "device/<int:device_id>/session/<session_id>",
        views.device_session,
        name="device_session",
    ),
    path("race/<int:race_id>", views.race, name="race"),
    path("race/<int:race_id>/point/all", views.point_all, name="point_all"),
    path("race/<int:race_id>/point/<int:point_id>", views.point, name="point"),
    path(
        "race/<int:race_id>/point/<int:point_id>/export",
        views.point_export,
        name="point_export",
    ),
]
