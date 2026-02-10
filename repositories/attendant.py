from typing import List
from bson import ObjectId
class AttendantRepository():
    def __init__(self, collection) -> None:
        self._collection = collection

    async def save(self, data:dict):
        result = await self._collection.insert_one(data)
        return result.inserted_id

    async def get_by_id(self, _id:str):
        result = await self._collection.find_one({"_id": ObjectId(_id)})
        return result

    async def update(self, _id:str, data:dict):
        result = await self._collection.update_one({"_id": ObjectId(_id)}, {"$set": data})
        return result.modified_count
    
    async def list(self, filter:dict = None):
        cursor = self._collection.find(filter or {})
        return await cursor.to_list(length=None)
    
    async def delete(self, _id:str):
        result = await self._collection.delete_one({"_id": ObjectId(_id)})
        return result.deleted_count