from motor.motor_asyncio import AsyncIOMotorCollection
from domain.chat.chats import  ChatStatus
from typing import Optional
from bson import ObjectId
from pymongo import ReturnDocument

def _serialize_doc(doc: dict) -> dict:
    """Convert MongoDB ObjectId to string for JSON serialization."""
    if doc is None:
        return None
    
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    
    return doc

class ChatRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    # ------------------------
    # Query Operations
    # ------------------------
    async def get_active_chats(self):
        try:
            cursor = self._collection.find({
                    "status": {
                        "$in": [
                            ChatStatus.ACTIVE.value,
                            ChatStatus.WAITING_MENU.value
                        ]
                    }
                },
                {"_id": 0}).sort("last_interaction_at", -1)
            
            return await cursor.to_list(length=None)
        
        except Exception:
            return None
        
    async def get_last_chat(self, phone: str) -> Optional[dict]:
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

    async def get_chats_by_attendant(self, 
                                        attendant_id: str, 
                                        limit:int = 50, 
                                        skip:int = 0):
        
        """Busca todas as sessões de um atendente, opcionalmente filtradas por status."""
        
        cursor = self._collection.find({"attendant_id": attendant_id}).sort("last_interaction_at", -1).limit(limit).skip(skip)

        async for doc in cursor:
            yield _serialize_doc(doc)

    async def get_all_chats(self,limit: int = 300, skip : int = 0):
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

    async def create_chat(self, chat: dict):
        result = await self._collection.find_one_and_update(
            {"phone_number": chat.get("phone_number")},
            {"$set": chat},
            upsert=True,
            return_document=True
        )
        return _serialize_doc(result)

    async def close_chat(self, phone: str):
        response=await self._collection.update_one(
            {"phone_number": phone, "status": {"$ne": ChatStatus.CLOSED.value}},
            {"$set": {"status": ChatStatus.CLOSED.value}}
        )
        return response.modified_count > 0
    
    async def update(self, data:dict, phone_number:str):
        # Update and return the updated document so callers receive the new state
        try:
            result = await self._collection.find_one_and_update(
                {"phone_number": phone_number},
                {"$set": data},
                return_document=ReturnDocument.AFTER
            )
            return _serialize_doc(result)
        except Exception:
            return None
    
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