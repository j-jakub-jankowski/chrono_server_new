from asgiref.sync import sync_to_async
from django.utils import timezone
from app.models import Device, DeviceData, InfoData, Error, DeviceSession, GunStart
from .parser import timestamp_from_string
import redis.asyncio as aioredis
from django.conf import settings


@sync_to_async
def db_get_device(device_number):
    chrono = Device.objects.get(device_number=device_number)
    return chrono


@sync_to_async
def db_get_device_session(device_number, date_time):
    session = DeviceSession.objects.get(
        device__device_number=device_number, date_time=date_time
    )
    return session


@sync_to_async
def db_save_device(device_number, device_name):
    chrono = Device.objects.create(
        device_number=device_number,
        device_name=device_name,
    )
    return chrono


@sync_to_async
def db_save_device_session(device, device_date, date_time):
    session = DeviceSession.objects.create(
        device=device, device_date=device_date, date_time=date_time
    )
    return session


@sync_to_async
def db_save_device(device_number, device_name):
    chrono = Device.objects.create(
        device_number=device_number,
        device_name=device_name,
    )
    return chrono


@sync_to_async
def db_save_connection_time(device_session, connection_time):
    device_session.connection_time = connection_time
    device_session.save()


@sync_to_async
def db_save_result_data(device_session, data, result_line):
    DeviceData.objects.create(
        device_session=device_session,
        sequence=data[1],
        tag=data[2],
        timer_code=data[3],
        event_code=data[4],
        time=data[5],
        reader_id=data[6],
        antenna=data[7],
        read_power=data[8],
        reader_sequence=data[9],
        read_type=data[10],
    )
    device_session.result_line = result_line
    device_session.save()


async def db_save_result_data_bulk(batch, device_session, result_line):
    """
    Zapisuje całą paczkę odczytów w jednym asynchronicznym zapytaniu INSERT SQL.
    chunk_data to lista krotek: [(surowe_data_list, line_number), ...]
    """
    objects_to_create = []

    for data in batch:
        # data[2] to tag, data[5] to time wg. komentarza w Twoim kodzie save_result
        obj = DeviceData(
            device_session=device_session,
            sequence=data[1],
            tag=data[2],
            timer_code=data[3],
            event_code=data[4],
            time=data[5],
            reader_id=data[6],
            antenna=data[7],
            read_power=data[8],
            reader_sequence=data[9],
            read_type=data[10],
        )
        objects_to_create.append(obj)

    if objects_to_create:
        # Django 4.2+ posiada natywną asynchroniczną metodę masowego zapisu
        await DeviceData.objects.abulk_create(objects_to_create)

    device_session.result_line = result_line
    await device_session.asave()


@sync_to_async
def db_save_info_data(device_session, data, info_line):
    InfoData.objects.create(
        device_session=device_session,
        info_device_id=data[1],
        line=data[2],
        info_type=data[3],
        time=timestamp_from_string(data[5]),
        info=data[6],
    )
    device_session.info_line = info_line
    device_session.save()


@sync_to_async
def db_save_connected(device_session, status):
    device_session.connected = status
    device_session.save()


@sync_to_async
def db_save_error(device_session, data):
    Error.objects.create(
        device_session=device_session,
        data=data,
    )


@sync_to_async
def db_save_gun_start(device_session, data):
    GunStart.objects.create(
        device_session=device_session,
        time=timestamp_from_string(data[5]),
    )


redis_async = aioredis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def rd_save_tag_to_stream(device_session_id, tag, time, device_name):

    await redis_async.xadd(
        f"stream_point_{device_session_id}",
        {"tag": tag, "time": time, "device_name": device_name},
        maxlen=100000,
        approximate=True,
    )


async def rd_save_tag_to_stream_bulk(batch, device_session_id, device_name):

    if not redis_async or not batch:
        return

    async with redis_async.pipeline(transaction=False) as pipe:
        for data in batch:
            stream_name = f"stream_point_{device_session_id}"
            fields = {"tag": data[2], "time": data[5], "device_name": device_name}
            pipe.xadd(stream_name, fields)

        await pipe.execute()
