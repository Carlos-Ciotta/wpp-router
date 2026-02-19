import redis.asyncio as redis
from datetime import datetime
import json

class DatabaseGuard:
    def __init__(self, main_db, redis_url="redis://localhost"):
        self.main_db = main_db
        self.queue = redis.from_url(redis_url)

    async def save_data(self, collection, data):
        try:
            # Tenta o banco principal
            return await self.main_db[collection].insert_one(data)
        except Exception as e:
            print(f"DB Principal OFF: Movendo para Fila de Backup. Erro: {e}")
            # Salva na fila do Redis com timestamp
            backup_payload = {"collection": collection, "data": data, "retry_at": datetime.now().timestamp()}
            await self.queue.lpush("db_backup_queue", json.dumps(backup_payload))
            return "queued"

    async def sync_backup_to_main(self):
        """Task que roda em background para limpar o backup"""
        while True:
            item = await self.queue.rpop("db_backup_queue")
            if not item:
                break
            payload = json.loads(item)
            try:
                await self.main_db[payload['collection']].insert_one(payload['data'])
            except:
                # Se falhar de novo, devolve para a fila
                await self.queue.lpush("db_backup_queue", item)
                break