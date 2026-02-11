from typing import List

class MessageRepository():
    def __init__(self, collection) -> None:
        self._collection = collection

    async def save_messages_bulk(self, messages: List[dict]) -> int:
        if not messages:
            return 0
        result = await self._collection.bulk_write(messages, ordered=False)
        return result.modified_count
        
    async def update_message_status_bulk(self, messages: List[dict]) -> int:
        if not messages:
            return 0
        result = await self._collection.updateMany(
            update={"$set": {"status": messages[0]["status"]}}
        )
        return result.modified_count