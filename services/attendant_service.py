from domain.attendants.attendant import Attendant

class AttendantService():
    def __init__(self, repository) -> None:
        self._repository = repository
    
    async def create_attendant(self, data:dict):
        try:
            attendant = Attendant(**data)
            return await self._repository.save(attendant.dict())
        except Exception as e:
            raise Exception(f"Error creating attendant: {str(e)}")
    
    async def get_attendant(self, _id:str):
        try:
            return await self._repository.get_by_id(_id)
        except Exception as e:
            raise Exception(f"Error fetching attendant: {str(e)}")
        
    async def update_attendant(self, _id:str, data:dict):
        try:
            return await self._repository.update(_id, data)
        except Exception as e:
            raise Exception(f"Error updating attendant: {str(e)}")
        
    async def list_attendants(self, filter:dict = None):
        try:
            return await self._repository.list(filter)
        except Exception as e:
            raise Exception(f"Error listing attendants: {str(e)}")
        
    async def delete_attendant(self, _id:str):
        try:
            return await self._repository.delete(_id)
        except Exception as e:
            raise Exception(f"Error deleting attendant: {str(e)}")
        