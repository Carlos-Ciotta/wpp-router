from domain.attendants.attendant import Attendant
from core.security import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta

class AttendantService():
    def __init__(self, repository) -> None:
        self._repository = repository
    
    async def create_attendant(self, data:dict):
        try:
            # Hash password before saving
            if "password" in data:
                data["password"] = get_password_hash(data["password"])
                
            attendant = Attendant(**data)
            return await self._repository.save(attendant.to_dict())
        except Exception as e:
            raise Exception(f"Error creating attendant: {str(e)}")
            
    async def authenticate_attendant(self, login: str, password: str):
        # We need a method to find by login in repo
        attendant = await self._repository.find_by_login(login)
        if not attendant:
            return None
        if not verify_password(password, attendant["password"]):
            return None
        return attendant
        
    async def create_token_for_attendant(self, attendant: dict):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": attendant["login"], "sector": attendant["sector"]},
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    
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
        