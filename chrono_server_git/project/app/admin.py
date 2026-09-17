from django.contrib import admin
from .models import (
    Device,
    DeviceSession,
    DeviceAssignment,
    Race,
    ControlPoint,
    DeviceData,
    InfoData,
    Error,
    GunStart,
)


from datetime import datetime, timezone

from django import forms

from .models import GunStart
from datetime import datetime, timezone


class GunStartAdminForm(forms.ModelForm):
    utc_time = forms.CharField(
        label="UTC",
        help_text="Format: DD.MM.YYYY HH:MM:SS.xx (UTC)",
    )

    class Meta:
        model = GunStart
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Przy edycji pokaż aktualną wartość
        if self.instance.pk:
            dt = datetime.fromtimestamp(self.instance.time, tz=timezone.utc)
            self.initial["utc_time"] = dt.strftime("%d.%m.%Y %H:%M:%S.%f")[:-4]

    def clean_utc_time(self):
        value = self.cleaned_data["utc_time"]

        try:
            dt = datetime.strptime(value, "%d.%m.%Y %H:%M:%S.%f")
        except ValueError:
            raise forms.ValidationError("Format: DD.MM.YYYY HH:MM:SS.xx")

        # Traktujemy wpis jako UTC - bez żadnych przeliczeń
        dt = dt.replace(tzinfo=timezone.utc)

        return dt.timestamp()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.time = self.cleaned_data["utc_time"]

        if commit:
            instance.save()

        return instance


def timestamp_to_datetime(value):
    if not value:
        return "-"

    return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%d.%m.%Y %H:%M:%S")


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("device_name", "device_number")


@admin.register(DeviceSession)
class DeviceSessionAdmin(admin.ModelAdmin):
    list_display = (
        "device",
        "device_date",
        "formatted_connection_time",
        "date_time",
        "result_line",
        "info_line",
        "connected",
    )

    # @admin.display(description="Date time")  # Nazwa kolumny w panelu admina
    # def formatted_date_time(self, obj):
    #     if obj.date_time:
    #         try:
    #             # 1. Konwersja timestampu (float/int) na obiekt datetime w UTC
    #             dt = datetime.fromtimestamp(float(obj.date_time), tz=timezone.utc)
    #             # 2. Formatowanie do oczekiwanego układu DD.MM.RRRR, HH:MM:SS
    #             return dt.strftime("%d.%m.%Y - %H:%M:%S")
    #         except (ValueError, TypeError):
    #             return obj.date_time  # Zwraca surową wartość w razie błędu konwersji
    #     return "-"

    @admin.display(description="Connection time")  # Nazwa kolumny w panelu admina
    def formatted_connection_time(self, obj):
        if obj.connection_time:
            try:
                # 1. Konwersja timestampu (float/int) na obiekt datetime w UTC
                dt = datetime.fromtimestamp(float(obj.connection_time), tz=timezone.utc)
                # 2. Formatowanie do oczekiwanego układu DD.MM.RRRR, HH:MM:SS
                return dt.strftime("%d.%m.%Y - %H:%M:%S")
            except (ValueError, TypeError):
                return (
                    obj.connection_time
                )  # Zwraca surową wartość w razie błędu konwersji
        return "-"


@admin.register(Race)
class RaceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "shift_time",
        "active",
    )

    list_filter = ("active",)

    search_fields = ("name",)


@admin.register(ControlPoint)
class ControlPointAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "race",
        # "minimal_time",
        # "mtbst",
    )

    list_filter = ("race",)

    search_fields = ("name",)


@admin.register(DeviceAssignment)
class DeviceAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "device",
        "control_point",
    )


@admin.register(DeviceData)
class DeviceDataAdmin(admin.ModelAdmin):
    list_display = (
        "device_session",
        "tag",
        "formatted_time",
        "reader_id",
        "read_type",
    )

    ordering = ("-time",)

    @admin.display(description="Time")  # Nazwa kolumny w panelu admina
    def formatted_time(self, obj):
        if obj.time:
            try:
                # 1. Konwersja timestampu (float/int) na obiekt datetime w UTC
                dt = datetime.fromtimestamp(float(obj.time), tz=timezone.utc)
                # 2. Formatowanie do oczekiwanego układu DD.MM.RRRR, HH:MM:SS
                return dt.strftime("%d.%m.%Y - %H:%M:%S.%f")[:-4]
            except (ValueError, TypeError):
                return obj.time  # Zwraca surową wartość w razie błędu konwersji
        return "-"


@admin.register(InfoData)
class InfoDataAdmin(admin.ModelAdmin):
    list_display = (
        "device_session",
        "info_device_id",
        "line",
        "info_type",
        "time",
        "info",
    )


@admin.register(Error)
class ErrorAdmin(admin.ModelAdmin):
    list_display = (
        "device_session",
        "data",
    )

    list_filter = ("device_session",)

    search_fields = ("data",)


@admin.register(GunStart)
class GunStartAdmin(admin.ModelAdmin):
    form = GunStartAdminForm

    fields = (
        "device_session",
        "utc_time",
    )
