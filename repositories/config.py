from motor.motor_asyncio import AsyncIOMotorCollection
from domain.config.chat_config import ChatConfig

class ConfigRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def get_config(self) -> ChatConfig:
        data = await self._collection.find_one({"type": "chat_config"})
        if data:
            return ChatConfig(**data)
        
        # Return default if not found
        return ChatConfig()

    async def save_config(self, config: ChatConfig):
        data = config.model_dump(exclude={"_id"})
        data["type"] = "chat_config"
        
        await self._collection.replace_one(
            {"type": "chat_config"},
            data,
            upsert=True
        )
        return config
