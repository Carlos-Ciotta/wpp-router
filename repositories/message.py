from typing import List
from pymongo import UpdateOne

class MessageRepository():
    def __init__(self, collection) -> None:
        self._collection = collection

    async def save_messages_bulk(self, messages: List[dict]) -> int:
        if not messages:
            return 0
        # Use insert_many for simple insertions instead of bulk_write with raw dicts
        result = await self._collection.insert_many(messages)
        return len(result.inserted_ids)
        
    async def update_message_status_bulk(self, messages: List[dict]) -> int:
        if not messages:
            return 0
        
        operations = []
        for msg in messages:
            # Match by message_id and update status
            operations.append(
                UpdateOne(
                    {"message_id": msg.get("message_id")}, 
                    {"$set": {"status": msg.get("status")}}
                )
            )
            
        if not operations:
            return 0
            
        result = await self._collection.bulk_write(operations, ordered=False)
        return result.modified_count