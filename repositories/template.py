from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import UpdateOne
from typing import List, Optional
from domain.template.template import Template
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

    async def save_templates(self, templates: List[Template]):
        if not templates:
            return
        
        operations = [
            UpdateOne(
                {"id": t.id}, 
                {"$set": t.to_dict()}, 
                upsert=True
            ) for t in templates
        ]
        
        await self._collection.bulk_write(operations)

    async def get_template_by_name(self, name: str) -> Optional[Template]:
        data = await self._collection.find_one({"name": name})
        return Template(**_serialize_doc(data)) if data else None

    async def list_templates(self) -> List[Template]:
        cursor = self._collection.find()
        templates = []
        async for doc in cursor:
            templates.append(Template(**_serialize_doc(doc)))
        return templates
