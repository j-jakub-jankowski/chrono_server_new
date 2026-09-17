from django.shortcuts import render, get_object_or_404
from .models import (
    ControlPoint,
    Device,
    DeviceData,
    DeviceSession,
    DeviceAssignment,
    GunStart,
    Race,
)
from django.db.models import F, Q
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Prefetch


def index(request):
    races = Race.objects.prefetch_related("control_points")
    devices = Device.objects.all()

    races_points = [
        {
            "id": race.id,
            "name": race.name,
            "active": race.active,
            "control_points": [
                {
                    "id": point.id,
                    "name": point.name,
                }
                for point in race.control_points.all()
            ],
        }
        for race in races
    ]

    context_data = {"races": races_points, "devices": devices}

    return render(request, "app/index.html", context_data)


def device_all(request):
    devices = Device.objects.all()

    context_data = {"devices": devices}

    return render(request, "app/device_all.html", context_data)


def device(request, device_id):
    _device = get_object_or_404(Device, id=device_id)
    _sessions = DeviceSession.objects.filter(device_id=device_id).order_by("-date_time")

    context_data = {}

    return render(request, "app/device.html", context_data)


def device_session(request, device_id, device_session_id):
    _device = get_object_or_404(Device, id=device_id)
    _device_session = get_object_or_404(DeviceSession, id=device_session_id)
    _tags = DeviceData.objects.filter(device_session=_device_session)

    context_data = {}

    return render(request, "app/device_session.html", context_data)


def race(request, race_id):
    race = get_object_or_404(Race, id=race_id)

    context_data = {"race": race}

    return render(request, "app/race.html", context_data)


def point_all(request, race_id):
    race = get_object_or_404(Race, id=race_id)

    points = ControlPoint.objects.filter(race_id=race_id).prefetch_related(
        Prefetch(
            "assignments",
            queryset=DeviceAssignment.objects.select_related("device"),
        )
    )

    points_devices = [
        {
            "id": point.id,
            "name": point.name,
            "alias": point.alias,
            "alias_id": point.alias_id,
            "devices": [
                {
                    "id": assignment.device.id,
                    "name": assignment.device.device_name,
                }
                for assignment in point.assignments.all()
            ],
        }
        for point in points
    ]

    context_data = {"race": race, "points_devices": points_devices}

    return render(request, "app/point_all.html", context_data)


def point(request, race_id, point_id):
    race = get_object_or_404(Race, id=race_id)
    control_point = get_object_or_404(ControlPoint, id=point_id)

    context_data = {"race": race, "control_point": control_point}

    return render(request, "app/point.html", context_data)


def point_export(request, race_id, point_id):
    q_race = get_object_or_404(Race, id=race_id)
    q_control_point = get_object_or_404(ControlPoint, id=point_id)

    assigned_device_ids = q_control_point.assignments.values_list(
        "device_id", flat=True
    )

    q_devices = (
        Device.objects.filter(id__in=assigned_device_ids)
        .prefetch_related(
            Prefetch(
                "sessions",
                queryset=DeviceSession.objects.order_by("-connection_time"),
            )
        )
        .order_by("device_number")
    )

    q_gunstarts = GunStart.objects.select_related("device_session__device").order_by(
        "-time"
    )

    race_data = {
        "id": q_race.id,
        "name": q_race.name,
        "active": q_race.active,
        "shift_time": q_race.shift_time_id,
    }

    control_point_data = {
        "id": q_control_point.id,
        "name": q_control_point.name,
        "race_id": q_control_point.race_id,
        "alias": q_control_point.alias,
        "alias_id": q_control_point.alias_id,
    }

    devices_data = [
        {
            "device_id": device.id,
            "device_number": device.device_number,
            "device_name": device.device_name,
            "sessions": [
                {
                    "id": session.id,
                    "device_date": session.device_date,
                    "connection_time": session.connection_time,
                    "date_time": session.date_time,
                    "result_line": session.result_line,
                    "info_line": session.info_line,
                    "connected": session.connected,
                }
                for session in device.sessions.all()
            ],
        }
        for device in q_devices
    ]

    gunstarts_data = []
    for gunstart in q_gunstarts:
        gunstarts_data.append(
            {
                "device_number": (
                    gunstart.device_session.device.device_number
                    if gunstart.device_session
                    else None
                ),
                "device_name": (
                    gunstart.device_session.device.device_name
                    if gunstart.device_session
                    else None
                ),
                "time": gunstart.time,
            }
        )

    context_data = {
        "race": race_data,
        "control_point": control_point_data,
        "devices": devices_data,
        "gunstarts": gunstarts_data,
    }

    return render(request, "app/point_export.html", context_data)
