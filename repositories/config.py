from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId

def _serialize_doc(doc: dict) -> dict:
    if doc is None:
        return None
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc

class ConfigRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def get_config(self) -> dict:
        data = await self._collection.find_one({"type": "chat_config"}) 
        return _serialize_doc(data)

    async def save_config(self, config: dict):
        data = config.model_dump(exclude={"_id"})
        data["type"] = "chat_config"
        
        await self._collection.replace_one(
            {"type": "chat_config"},
            data,
            upsert=True
        )
        return config
