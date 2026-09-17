from django.db import models
from datetime import datetime, timezone


class BaseModel(models.Model):
    objects = models.Manager()

    class Meta:
        abstract = True


class Device(BaseModel):
    device_number = models.CharField(max_length=20)
    device_name = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.device_name}"


class DeviceSession(BaseModel):
    device = models.ForeignKey(
        "Device", on_delete=models.CASCADE, related_name="sessions"
    )
    device_date = models.CharField(max_length=20)
    connection_time = models.FloatField(blank=True, null=True)
    date_time = models.CharField(max_length=8)
    result_line = models.IntegerField(default=1)
    info_line = models.IntegerField(default=1)
    connected = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["device", "date_time"],
                name="unique_device_datetime",
            )
        ]

    def __str__(self):
        return f"{self.device} - {self.date_time}"


class DeviceAssignment(BaseModel):
    device = models.ForeignKey(
        "Device", on_delete=models.CASCADE, related_name="assignments"
    )
    control_point = models.ForeignKey(
        "ControlPoint", on_delete=models.CASCADE, related_name="assignments"
    )
    # shift_time = models.FloatField(default=0)


class Race(BaseModel):
    name = models.CharField(max_length=20)
    active = models.BooleanField(default=False)
    shift_time = models.ForeignKey(
        "GunStart",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.name}"


class GunStart(BaseModel):
    device_session = models.ForeignKey(
        "DeviceSession", on_delete=models.CASCADE, blank=True, null=True
    )
    time = models.FloatField()

    class Meta:
        ordering = ["-time"]

    def __str__(self):
        dt = datetime.fromtimestamp(self.time, tz=timezone.utc)
        return f"{self.device_session} - {dt.strftime('%y-%m-%d %H:%M:%S.%f')[:-4]}"


class ControlPoint(BaseModel):
    name = models.CharField(max_length=20)
    race = models.ForeignKey(
        Race, on_delete=models.CASCADE, related_name="control_points"
    )
    alias = models.CharField(max_length=20, blank=True, null=True)
    alias_id = models.CharField(max_length=20, blank=True, null=True)
    # minimal_time = models.ForeignKey(
    #     "GunStart",
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    # )
    # mtbst = models.IntegerField(default=300)

    def __str__(self):
        return f"{self.name}"


class DeviceData(BaseModel):
    device_session = models.ForeignKey("DeviceSession", on_delete=models.CASCADE)
    sequence = models.IntegerField()
    tag = models.IntegerField()
    timer_code = models.IntegerField()
    event_code = models.IntegerField()
    time = models.FloatField()
    reader_id = models.CharField(max_length=20)
    antenna = models.CharField(max_length=20)
    read_power = models.CharField(max_length=20)
    reader_sequence = models.CharField(max_length=20)
    read_type = models.CharField(max_length=1)

    def __str__(self):
        return f"{self.tag} --- {self.time}"


class InfoData(BaseModel):
    device_session = models.ForeignKey("DeviceSession", on_delete=models.CASCADE)
    info_device_id = models.CharField(max_length=20)
    line = models.IntegerField()
    info_type = models.CharField(max_length=20)
    time = models.FloatField()
    info = models.CharField(max_length=20)


class Error(BaseModel):
    device_session = models.ForeignKey("DeviceSession", on_delete=models.CASCADE)
    data = models.CharField(max_length=200)


# class PointData(BaseModel):
#     control_point = models.ForeignKey("ControlPoint", on_delete=models.CASCADE)
#     device_session = models.ForeignKey("DeviceSession", on_delete=models.CASCADE)
#     sequence = models.IntegerField()
#     tag = models.IntegerField()
#     time = models.FloatField()
#     ignored = models.BooleanField(default=False)
#     by_hand = models.BooleanField(default=False)
#     description = models.CharField(max_length=200, blank=True)
