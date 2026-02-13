from motor.motor_asyncio import AsyncIOMotorCollection
from domain.contact.contact import Contact
from datetime import datetime
from typing import Optional
from bson import ObjectId

def _serialize_doc(doc: dict) -> dict:
    if doc is None:
        return None
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc

class ContactRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def update_contact(self, phone: str, name: str, timestamp: float) -> None:
        """
        Atualiza ou cria um contato (Upsert).
        Sempre atualiza:
        - O nome (se fornecido, pois o nome no WhatsApp pode mudar)
        - updated_at
        - last_message_at
        
        Se for inserção, created_at é setado.
        """
        update_data = {
            "updated_at": datetime.now().timestamp(),
            "last_message_at": timestamp
        }
        
        if name:
            update_data["name"] = name
            
        await self._collection.update_one(
            {"_id": phone},
            {
                "$set": update_data,
                "$setOnInsert": {"created_at": datetime.now().timestamp()}
            },
            upsert=True
        )

    async def get_by_phone(self, phone: str) -> Optional[Contact]:
        data = await self._collection.find_one({"_id": phone})
        if data:
            return Contact(**_serialize_doc(data))
        return None

    async def list_contacts(self, limit: int = 50, skip: int = 0) -> list[Contact]:
        cursor = self._collection.find().sort("last_message_at", -1).skip(skip).limit(limit)
        contacts = []
        async for doc in cursor:
            contacts.append(Contact(**_serialize_doc(doc)))
        return contacts
