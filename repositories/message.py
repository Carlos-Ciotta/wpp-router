from typing import List
from pymongo import UpdateOne
from bson import ObjectId

def _serialize_doc(doc: dict) -> dict:
    if doc is None:
        return None
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc

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
    
    async def get_messages_by_phone_number(self, phone_number: str, limit:int, skip:int):
        cursor = self._collection.find({"phone_number": phone_number})\
            .sort("timestamp", -1)\
            .skip(skip)\
            .limit(limit)
        async for message in cursor:
            yield _serialize_doc(message)
    
    async def get_messages_before(self, phone: str, timestamp: str, limit: int):
        """Busca mensagens mais antigas que um determinado ponto."""
        cursor = self._collection.find({
            "phone_number": phone,
            "timestamp": {"$lt": timestamp}
        }).sort("timestamp", -1).limit(limit)
        
        async for msg in cursor:
            yield _serialize_doc(msg)

    async def watch_new_messages(self, phone: str):
        """Abre um stream de mudanças no MongoDB."""
        pipeline = [{"$match": {"operationType": "insert", "fullDocument.phone_number": phone}}]
        # full_document="updateLookup" garante que recebemos o objeto inteiro
        async with self._collection.watch(pipeline, full_document="updateLookup") as stream:
            async for change in stream:
                yield _serialize_doc(change["fullDocument"])