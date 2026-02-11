from motor.motor_asyncio import AsyncIOMotorCollection

class ConfigRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def get_config(self) -> dict:
        data = await self._collection.find_one({"type": "chat_config"}) 
        # Return default if not found
        return data

    async def save_config(self, config: dict):
        data = config.model_dump(exclude={"_id"})
        data["type"] = "chat_config"
        
        await self._collection.replace_one(
            {"type": "chat_config"},
            data,
            upsert=True
        )
        return config
