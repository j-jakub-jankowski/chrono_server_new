import asyncio
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
import os


from .client import Client
from .crud import (
    db_get_device,
    db_save_device,
    db_save_connection_time,
    db_get_device_session,
    db_save_device_session,
)
from .parser import (
    timestamp_from_string,
    timestamp_from_short_string,
    date_time_from_short_string,
)


class Server:
    @staticmethod
    async def new_client(reader, writer):
        hello_from_chrono = (await reader.readline()).decode("utf8").rstrip()
        print(hello_from_chrono)

        try:
            (
                device_number,
                device_date,
                device_name,
                _,
                _,
                connection_time,
                _,
                date_time,
            ) = hello_from_chrono.split("~")

            print(device_number, device_date, device_name, connection_time, date_time)

        except Exception as e:
            print(f"Niepoprawny format danych: {hello_from_chrono} error: {e} ")
            writer.close()
            await writer.wait_closed()
            return

        try:
            device = await db_get_device(device_number)
        except ObjectDoesNotExist:
            device = await db_save_device(device_number, device_name)

        try:
            device_session = await db_get_device_session(device_number, date_time)
        except ObjectDoesNotExist:
            device_session = await db_save_device_session(
                device, device_date, date_time
            )

        await db_save_connection_time(
            device_session, timestamp_from_string(connection_time)
        )
        client = Client(reader, writer, device, device_session)
        asyncio.create_task(client.handshake())


def start_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    server = Server()

    loop.create_task(asyncio.start_server(server.new_client, "57.128.197.192", 61610))

    print(f"TCP SOCKET SERVER STARTED")
    print(timezone.localtime().strftime("%H:%M:%S"))

    loop.run_forever()
