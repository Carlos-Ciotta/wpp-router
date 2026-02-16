from motor.motor_asyncio import AsyncIOMotorCollection
from domain.session.chat_session import  SessionStatus
from typing import Optional
from datetime import datetime
from bson import ObjectId

def _serialize_doc(doc: dict) -> dict:
    """Convert MongoDB ObjectId to string for JSON serialization."""
    if doc is None:
        return None
    
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    
    return doc

class SessionRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    # ------------------------
    # Query Operations
    # ------------------------
    async def get_active_sessions(self):
        try:
            cursor = self._collection.find({
                    "status": {
                        "$in": [
                            SessionStatus.ACTIVE.value,
                            SessionStatus.WAITING_MENU.value
                        ]
                    }
                },
                {"_id": 0}).sort("last_interaction_at", -1)
            
            return await cursor.to_list(length=None)
        
        except Exception:
            return None
        
    async def get_last_session(self, phone: str) -> Optional[dict]:
        """Recupera a última sessão do cliente, independente do status."""
        cursor = self._collection.find({"phone_number": phone}).sort("last_interaction_at", -1).limit(1)
        # Note: sort by last_interaction_at desc
        try:
            # Motor 3.0+ syntax for finding one usually implies await find_one or iterating cursor
            # If using find().limit(1), we need to iterate or to_list
            results = await cursor.to_list(length=1)
            if results:
                doc = _serialize_doc(results[0])
                return doc
        except Exception:
            return None
        return None

    async def get_sessions_by_attendant(self, 
                                        attendant_id: str, 
                                        limit:int = 50, 
                                        skip:int = 0):
        
        """Busca todas as sessões de um atendente, opcionalmente filtradas por status."""
        
        cursor = self._collection.find({"attendant_id": attendant_id}).sort("last_interaction_at", -1).limit(limit).skip(skip)

        async for doc in cursor:
            yield _serialize_doc(doc)

    async def get_all_sessions(self,limit: int = 300, skip : int = 0):
        """Busca todas as sessões, opcionalmente filtradas por status."""
        
        cursor = self._collection.find().sort("last_interaction_at", -1).limit(limit).skip(skip)

        async for doc in cursor:
            yield _serialize_doc(doc)
    
    async def get_last_assigned_attendant_id(self):
        """Recupera o ID do último atendente atribuído a uma sessão ativa."""
        cursor = self._collection.find({"attendant_id": {"$ne": None}}).sort("last_interaction_at", -1).limit(1)
        results = await cursor.to_list(length=1)
        if results:
                return results[0].get("attendant_id")
        return None
    # CRUD Operations

    async def create_session(self, session: dict):
        result = await self._collection.find_one_and_update(
            {"phone_number": session.get("phone_number")},
            {"$set": session},
            upsert=True,
            return_document=True
        )
        return _serialize_doc(result)

    async def close_session(self, phone: str):
        response=await self._collection.update_one(
            {"phone_number": phone, "status": {"$ne": SessionStatus.CLOSED.value}},
            {"$set": {"status": SessionStatus.CLOSED.value}}
        )
        return response.modified_count > 0
    
    async def update(self, data:dict, phone_number:str):
        response = await self._collection.update_one({"phone_number": phone_number}, {"$set": data})

        return response.modified_count > 0
    
    async def assign_attendant(self, phone: str, attendant_id: str, category: str):
        response = await self._collection.update_one(
            {"phone_number": phone},
            {
                "$set": {
                    "attendant_id": attendant_id,
                    "category": category
                }
            }
        )

        return response.modified_count > 0