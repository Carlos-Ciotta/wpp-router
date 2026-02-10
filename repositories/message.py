from typing import List
from pymongo import UpdateOne

class MessageRepository():
    def __init__(self, collection) -> None:
        self._collection = collection

    async def save_messages_bulk(self, messages: List[dict]) -> int:
        if not messages:
            return 0
        
        operations = []
        for msg in messages:
            # Se tiver message_id, usa como chave única para upsert
            if "message_id" in msg:
                operations.append(
                    UpdateOne(
                        {"message_id": msg["message_id"]},
                        {"$set": msg},
                        upsert=True
                    )
                )

        if operations:
            result = await self._collection.bulk_write(operations)
            return result.upserted_count + result.modified_count
        
        return 0