# app/broadcaster.py
import asyncio
import json


class Broadcaster:
    def __init__(self):
        self.clients = {}
        self.lock = asyncio.Lock()
        self._id_counter = 0

    async def connect(self, websocket):
        async with self.lock:
            client_id = self._id_counter
            self._id_counter += 1
            self.clients[client_id] = websocket
        return client_id

    async def disconnect(self, client_id):
        async with self.lock:
            if client_id in self.clients:
                try:
                    await self.clients[client_id].close()
                except:
                    pass  # Ignore close errors
                del self.clients[client_id]

    async def broadcast_json(self, message: dict):
        text = json.dumps(message)
        to_remove = []
        async with self.lock:
            for cid, ws in list(self.clients.items()):
                try:
                    await ws.send_text(text)
                except Exception:
                    to_remove.append(cid)
            for cid in to_remove:
                if cid in self.clients:
                    del self.clients[cid]
