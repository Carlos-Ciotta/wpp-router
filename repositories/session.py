from motor.motor_asyncio import AsyncIOMotorCollection
from domain.session.chat_session import ChatSession, SessionStatus
from typing import Optional
from datetime import datetime

class SessionRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def get_active_session(self, phone: str) -> Optional[ChatSession]:
        data = await self._collection.find_one({
            "phone_number": phone, 
            "status": {"$ne": SessionStatus.CLOSED.value}
        })
        if data:
            return ChatSession(**data)
        return None

    async def create_session(self, session: ChatSession):
        await self._collection.insert_one(session.dict(exclude={"_id"}))
        return session

    async def update_last_interaction(self, phone: str):
        await self._collection.update_one(
            {"phone_number": phone, "status": {"$ne": SessionStatus.CLOSED.value}},
            {"$set": {"last_interaction_at": datetime.now()}}
        )

    async def close_session(self, phone: str):
        await self._collection.update_one(
            {"phone_number": phone, "status": {"$ne": SessionStatus.CLOSED.value}},
            {"$set": {"status": SessionStatus.CLOSED.value}}
        )

    async def assign_attendant(self, phone: str, attendant_id: str, category: str):
        await self._collection.update_one(
            {"phone_number": phone, "status": {"$ne": SessionStatus.CLOSED.value}},
            {
                "$set": {
                    "status": SessionStatus.ACTIVE.value,
                    "attendant_id": attendant_id,
                    "category": category,
                    "last_interaction_at": datetime.now()
                }
            }
        )
