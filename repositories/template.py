from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import UpdateOne
from typing import List, Optional
from bson import ObjectId

def _serialize_doc(doc: dict) -> dict:
    if doc is None:
        return None
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc

class TemplateRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def save_templates(self, templates: List[dict]):
        if not templates:
            return
        
        operations = [
            UpdateOne(
                {"id": t.get("id")}, 
                {"$set": t}, 
                upsert=True
            ) for t in templates
        ]
        
        await self._collection.bulk_write(operations)

    async def get_template_by_name(self, name: str) -> Optional[dict]:
        data = await self._collection.find_one({"name": name})
        return _serialize_doc(data)

    async def list_templates(self) -> List[dict]:
        cursor = self._collection.find()
        templates = []
        async for doc in cursor:
            templates.append(_serialize_doc(doc))
        return templates
