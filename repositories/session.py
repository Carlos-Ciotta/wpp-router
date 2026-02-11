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

    async def get_last_session(self, phone: str) -> Optional[ChatSession]:
        """Recupera a última sessão do cliente, independente do status."""
        cursor = self._collection.find({"phone_number": phone}).sort("last_interaction_at", -1).limit(1)
        # Note: sort by last_interaction_at desc
        try:
            # Motor 3.0+ syntax for finding one usually implies await find_one or iterating cursor
            # If using find().limit(1), we need to iterate or to_list
            results = await cursor.to_list(length=1)
            if results:
                return ChatSession(**results[0])
        except Exception:
            return None
        return None

    async def create_session(self, session: ChatSession):
        await self._collection.insert_one(session.dict(exclude={"_id"}))
        return session

    async def update_last_interaction(self, phone: str, interaction_time: datetime = None):
        if interaction_time is None:
            interaction_time = datetime.now()
        await self._collection.update_one(
            {"phone_number": phone, "status": {"$ne": SessionStatus.CLOSED.value}},
            {"$set": {"last_interaction_at": interaction_time}}
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

    async def get_last_assigned_attendant_id(self, category: str) -> Optional[str]:
        try:
            # Find the most recent session with an attendant assigned (not a QUEUE)
            # Assuming real attendants have ObjectId-like strings, queues are "QUEUE_..."
            cursor = self._collection.find(
                {
                    "category": category, 
                    "attendant_id": {"$exists": True, "$ne": None}
                }
            ).sort("last_interaction_at", -1).limit(1)
            
            async for doc in cursor:
                return doc.get("attendant_id")
        except:
            pass
        return None
