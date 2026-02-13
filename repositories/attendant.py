from typing import List
from bson import ObjectId

def _serialize_doc(doc: dict) -> dict:
    if doc is None:
        return None
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc

class AttendantRepository():
    def __init__(self, collection) -> None:
        self._collection = collection

    async def save(self, data:dict):
        result = await self._collection.insert_one(data)
        return str(result.inserted_id)

    async def get_by_id(self, _id:str):
        result = await self._collection.find_one({"_id": ObjectId(_id)})
        return _serialize_doc(result)

    async def update(self, _id:str, data:dict):
        result = await self._collection.update_one({"_id": ObjectId(_id)}, {"$set": data})
        return result.modified_count
    
    async def list(self, filter:dict = None):
        cursor = self._collection.find(filter or {})
        results = await cursor.to_list(length=None)
        return [_serialize_doc(doc) for doc in results]
    
    async def delete(self, _id:str):
        result = await self._collection.delete_one({"_id": ObjectId(_id)})
        return result.deleted_count

    async def find_by_client_and_sector(self, client_phone: str, sector: str):
        # Case insensitive sector search might be good, but strict for now
        result = await self._collection.find_one({
            "clients": client_phone,
            "sector": {"$in": [sector]}
        })
        return _serialize_doc(result)

    async def find_by_login(self, login: str):
        result = await self._collection.find_one({"login": login})
        return _serialize_doc(result)