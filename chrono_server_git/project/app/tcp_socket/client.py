import asyncio
from datetime import timedelta
from django.utils import timezone
from .crud import (
    db_save_result_data,
    db_save_info_data,
    db_save_connected,
    db_save_error,
    db_save_gun_start,
    rd_save_tag_to_stream,
    db_save_result_data_bulk,
    rd_save_tag_to_stream_bulk,
)
from .parser import check_data_type, timestamp_from_string


class Client:
    def __init__(self, reader, writer, device, device_session):
        self.active = True
        self.reader = reader
        self.writer = writer
        self.device = device
        self.device_session = device_session

        self.actual_result_line = self.device_session.result_line
        self.actual_info_line = self.device_session.info_line

        self.last_read_time = timezone.now()

        self.db_queue = asyncio.Queue()

        self._tasks = []

    async def handshake(self):
        await self.send_response("ACK~ServerBibTag~57.128.197.192~2.0.0\r\n")

        loop = asyncio.get_running_loop()
        self._tasks = [
            loop.create_task(self.start_line_info(self.actual_info_line)),
            loop.create_task(self.start_line_result(self.actual_result_line)),
            loop.create_task(self.start_reading()),
            loop.create_task(self.check_connection()),
            loop.create_task(self.db_consumer_worker()),
        ]
        await self.connected()

    async def start_line_result(self, line):
        """send message to device where to start reading results"""
        await self.send_response(f"RR~{line}\r\n")

    async def start_line_info(self, line):
        """send massage to device where to start reading information data"""
        await self.send_response(f"MR~~{line}\r\n")

    async def handle_data(self):
        """
        get message from device, split into list and check type
        :return: list, int
        """
        data = (await self.reader.readline()).decode("utf8").rstrip().split("~")
        # print(f"Received data: {data}")
        data_type = check_data_type(data)
        self.last_read_time = timezone.now()
        return data, data_type

    async def send_response(self, data):
        """send message to device"""
        print(f"Sending response: {data.strip()}")
        if not self.active:
            return
        try:
            self.writer.write(data.encode("utf8"))
            await self.writer.drain()
        except ConnectionResetError:
            await self.disconnected()

    async def start_reading(self):
        """start reading messages from device"""
        while self.active:
            data, data_type = await self.handle_data()
            if data == [""]:
                await self.disconnected()
                break
            if data_type == 4:
                await self.pong()
            elif data_type == 1 or data_type == 2 or data_type == 3:
                await self.db_queue.put(data)
                # await self.save_result(data)
            elif data_type == 6:
                await self.save_info(data)
                if data[3] == "Gun":
                    await self.save_gun_start(data)
            elif data_type == 9:
                await self.error_data(data)

    async def db_consumer_worker(self):
        BATCH_SIZE = 200
        BATCH_TIMEOUT = 0.2
        batch = []

        while True:
            try:
                if not batch:
                    data = await self.db_queue.get()
                    self.actual_result_line += 1
                    batch.append(data)

                start_time = asyncio.get_running_loop().time()
                while len(batch) < BATCH_SIZE:
                    time_left = BATCH_TIMEOUT - (
                        asyncio.get_running_loop().time() - start_time
                    )
                    if time_left <= 0:
                        break

                    try:
                        data = await asyncio.wait_for(
                            self.db_queue.get(), timeout=max(0.001, time_left)
                        )
                        self.actual_result_line += 1
                        batch.append((data))

                    except asyncio.TimeoutError:
                        break

                # Jeśli zebraliśmy odczyty, wykonujemy masowe zapisy jednym strzałem
                if batch:
                    await db_save_result_data_bulk(
                        batch, self.device_session, self.actual_result_line
                    )
                    await rd_save_tag_to_stream_bulk(
                        batch,
                        self.device_session.id,
                        self.device.device_name,
                    )

                    for _ in range(len(batch)):
                        self.db_queue.task_done()
                    batch.clear()

            except asyncio.CancelledError:
                # ZABEZPIECZENIE: Jeśli zadanie jest anulowane (np. zamknięcie serwera),
                # awaryjnie opróżniamy lokalny bufor 'chunk' bezpośrednio do baz danych.
                if batch:
                    try:
                        await db_save_result_data_bulk(
                            batch, self.device_session, self.actual_result_line
                        )
                        await rd_save_tag_to_stream_bulk(
                            batch,
                            self.device_session.id,
                            self.device.device_name,
                        )
                        for _ in range(len(batch)):
                            self.db_queue.task_done()

                    except Exception as e:
                        print(f"Błąd awaryjnego zrzutu bufora przy zamykaniu: {e}")
                raise

            except Exception as e:
                print(f"Błąd krytyczny w masowym workerze bazy danych: {e}")
                for _ in range(len(batch)):
                    self.db_queue.task_done()
                batch.clear()

    # async def save_result(self, data):
    #     """
    #     save results in database
    #     ['cmd',
    #     'sequence',
    #     'tag',
    #     'timer code', 9 - good , 0 - bad
    #     'event code', 1 - good, 0 - bad
    #     'time',
    #     'reader ID',
    #     'antenna', 1, 2, 4, 8 - binary 0000
    #     'read power', lower - better
    #     'reader sequence',
    #     'read type', P I K
    #     'XXX']
    #     :param data:
    #     :return:

    #     """
    #     self.actual_result_line += 1
    #     await db_save_result_data(self.device_session, data, self.actual_result_line)
    #     await rd_save_tag_to_stream(
    #         self.device_session.id, data[2], data[5], self.device.device_name
    #     )

    async def save_gun_start(self, data):
        """
        save information from device into database
        """
        await db_save_gun_start(self.device_session, data)

    async def save_info(self, data):
        """
        save information from device into database
        """
        self.actual_info_line += 1
        await db_save_info_data(self.device_session, data, self.actual_info_line)

    async def check_connection(self):
        while self.active:
            now = timezone.now()
            if now - self.last_read_time > timedelta(seconds=100):
                await self.disconnected()
                break
            await asyncio.sleep(5)

    async def connected(self):
        """
        device connected
        """
        await db_save_connected(self.device_session, True)

    async def disconnected(self):
        """
        device disconnected
        """
        print("Connection ended.")
        await db_save_connected(self.device_session, False)

        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception as e:
            print(f"Close error: {e}")

        current = asyncio.current_task()

        for t in self._tasks:
            if t != current:
                t.cancel()

        for t in self._tasks:
            if t != current:
                try:
                    await t
                except asyncio.CancelledError:
                    pass

        self.active = False

    async def pong(self):
        """
        send response to PING from device
        """
        await self.send_response("ACK~PING\r\n")

    def check_ping_time(self):
        # TODO: check time, alert about desynchronization
        pass

    async def error_data(self, data):
        """save data with incorrect type to database"""
        await db_save_error(self.device_session, data)
