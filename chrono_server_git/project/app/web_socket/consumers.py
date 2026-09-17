import asyncio
import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer
import redis.asyncio as aioredis
from django.conf import settings


class PointConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis_async = None
        self.read_task = None
        self.flush_task = None
        self.buffer = []
        self.buffer_lock = asyncio.Lock()

        self.last_ids = {}

        self.BATCH_SIZE_LIVE = 100
        self.BATCH_SIZE_HISTORY = 1000
        self.BATCH_INTERVAL_SEC = 0.5

    async def connect(self):
        await self.accept()
        self.redis_async = aioredis.Redis.from_url(
            settings.REDIS_URL, decode_responses=True
        )

    async def disconnect(self, close_code):
        # Pełne i bezpieczne zatrzymanie pętli w tle przed zamknięciem połączenia
        await self.stop_streaming()

        if self.redis_async:
            await self.redis_async.close()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)

            command_type = data.get("type")

            if command_type == "start_stream":

                selected_sessions = data.get("selected_session_ids", {})

                streams_to_read = {}
                if not selected_sessions:
                    await self.send(
                        json.dumps(
                            {"type": "error", "context": "Brak podanych nazw streamów."}
                        )
                    )
                    return

                streams_to_read = {}

                for info in selected_sessions.values():
                    if isinstance(info, dict) and info.get("session_id"):
                        stream_name = f"stream_point_{info.get('session_id')}"
                        last_id = "0-0"
                        streams_to_read[stream_name] = last_id

                await self.start_streaming(streams_to_read, history=True)

            elif command_type == "resume_stream":
                if not data.get("last_ids"):
                    await self.send(
                        json.dumps({"error": "Brak podanych nazw streamów."})
                    )
                    return
                # Wznowienie – priorytet mają ID przysłane przez klienta (frontend)
                provided_ids = data.get("last_ids", {})
                self.last_ids.update(provided_ids)

                streams_to_read = {
                    name: self.last_ids.get(name, "0-0") for name in provided_ids
                }
                print(streams_to_read)
                await self.start_streaming(streams_to_read, history=False)

            elif command_type == "info":
                print(data["data"])

            else:
                await self.send(
                    json.dumps({"type": "error", "context": "Nieznana komenda."})
                )

        except Exception as e:
            await self.send(
                json.dumps({"type": "error", "context": f"Błąd parsowania: {str(e)}"})
            )

    async def start_streaming(self, streams_to_read, history):
        """Uruchamia procesy czytania i opróżniania bufora w tle"""
        await self.stop_streaming()

        async with self.buffer_lock:
            self.buffer.clear()

        # POPRAWIONE: dynamiczne przekazywanie parametru history zamiast sztywnego False
        self.read_task = asyncio.create_task(
            self.get_and_listen(streams_to_read, history=history)
        )
        self.flush_task = asyncio.create_task(self.batch_timer_loop())

    async def get_and_listen(self, streams_to_read, history):
        try:
            if history:
                all_unordered_tags = []
                await self.send(
                    json.dumps({"type": "status", "context": "pobieranie_historii"})
                )

                while True:
                    raw_data = await self.redis_async.xread(
                        streams=streams_to_read, count=1000
                    )
                    if not raw_data:
                        break
                    new_tags = False
                    for stream_name, messages in raw_data:
                        if messages:
                            new_tags = True
                            for msg_id, msg_data in messages:
                                all_unordered_tags.append(
                                    (msg_id, stream_name, msg_data)
                                )
                            streams_to_read[stream_name] = messages[-1][0]
                    if not new_tags:
                        break

                # Sortowanie wiadomości po ID Redis (timestamp-sekwencja)
                ordered_tags = sorted(
                    all_unordered_tags, key=lambda x: float(x[2]["time"])
                )

                if ordered_tags:
                    payload = [
                        {
                            "stream_tag_id": msg_id,
                            "stream_name": stream,
                            "read": msg_data,
                        }
                        for msg_id, stream, msg_data in ordered_tags
                    ]

                    for i in range(0, len(payload), self.BATCH_SIZE_HISTORY):
                        batch = payload[i : i + self.BATCH_SIZE_HISTORY]
                        await self.send(
                            json.dumps(
                                {
                                    "type": "history_batch",
                                    "count": len(batch),
                                    "tags": batch,
                                }
                            )
                        )
                        # Krótki odpoczynek asynchroniczny, aby nie zablokować pętli zdarzeń
                        await asyncio.sleep(0.01)

                async with self.buffer_lock:
                    self.last_ids = {
                        stream: last_id for stream, last_id in streams_to_read.items()
                    }

            else:
                async with self.buffer_lock:
                    for stream, last_id in streams_to_read.items():
                        if stream not in self.last_ids:
                            self.last_ids[stream] = last_id

            await self.send(
                json.dumps({"type": "status", "context": "tryb_live_aktywny"})
            )

            while True:
                async with self.buffer_lock:
                    current_streams = {
                        stream: last_id for stream, last_id in self.last_ids.items()
                    }

                if not current_streams:
                    await asyncio.sleep(0.1)
                    continue

                # Odczyt blokujący – optymalne obciążenie CPU
                live_data = await self.redis_async.xread(
                    streams=current_streams, count=100, block=1000
                )

                if live_data:
                    trigger_flush = False

                    async with self.buffer_lock:
                        for stream_name, messages in live_data:
                            for msg_id, msg_data in messages:
                                self.buffer.append(
                                    {
                                        "read": msg_data,
                                        "stream_name": stream_name,
                                        "stream_tag_id": msg_id,
                                    }
                                )
                                self.last_ids[stream_name] = msg_id

                        if len(self.buffer) >= self.BATCH_SIZE_LIVE:
                            trigger_flush = True

                    if trigger_flush:
                        await self.flush_buffer()

        except asyncio.CancelledError:
            # Prawidłowe zachowanie przy anulowaniu zadania
            raise
        except Exception as e:
            try:
                await self.send(
                    json.dumps(
                        {
                            "type": "error",
                            "context": f"Błąd krytyczny strumienia: {str(e)}",
                        }
                    )
                )
            except Exception:
                pass

    async def stop_streaming(self):
        """Zatrzymuje zadania w tle i czeka na ich pełne zakończenie"""
        if self.read_task:
            self.read_task.cancel()
        if self.flush_task:
            self.flush_task.cancel()

        if self.read_task or self.flush_task:
            # Oczekiwanie na zakończenie, by zapobiec wyciekom zadań (Task Leaks)
            await asyncio.gather(
                self.read_task, self.flush_task, return_exceptions=True
            )
            self.read_task = None
            self.flush_task = None

    async def batch_timer_loop(self):
        try:
            while True:
                await asyncio.sleep(self.BATCH_INTERVAL_SEC)
                await self.flush_buffer()
        except asyncio.CancelledError:
            raise

    async def flush_buffer(self):
        batch_to_send = []
        async with self.buffer_lock:
            if self.buffer:
                batch_to_send = list(self.buffer)
                self.buffer.clear()

        if batch_to_send:
            try:
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "live_batch",
                            "count": len(batch_to_send),
                            "tags": batch_to_send,
                        }
                    )
                )
            except Exception:
                # Zabezpieczenie na wypadek, gdyby gniazdo zostało zamknięte w trakcie wysyłki
                pass
