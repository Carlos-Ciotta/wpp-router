from typing import List

class MessageRepository():
    def __init__(self, collection) -> None:
        self._collection = collection

    async def save_messages_bulk(self, messages: List[dict]) -> int:
        if not messages:
            return 0

        result = await self._collection.insert_many(messages)
        return len(result.inserted_ids)