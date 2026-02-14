from domain.attendants.attendant import Attendant
from repositories.attendant import AttendantRepository
from core.security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta
from utils.cache import Cache

class AttendantService():
    def __init__(self, repository:AttendantRepository,
                 cache:Cache) -> None:
        self._repository = repository
        self._cache = cache

    # ----------------
    # Cache
    # ----------------
    async def reset_users_cache(self):
        try:
            if await self._cache.ensure():
                await self._cache.delete("users")
                users = await self._repository.list()
                await self._cache.set("users", users)
        except Exception as e:
            raise Exception(f"Error during cache reset: {e}")

    async def get_users_cached(self):
        try:
            if await self._cache.ensure():
                return await self._cache.get("users")
            return None
        except Exception as e:
             raise Exception(f"Error during cache search: {e}")

    # ----------------
    # Helpers
    # ----------------
    async def find_by_login(self, login: str):
        try:
            cached_users = await self.get_users_cached()
            if cached_users:
                for u in cached_users:
                    if u.get("login") == login:
                        return u
            
            return await self._repository.find_by_login(login)
        except Exception as e:
            raise Exception(f"Error finding attendant by login: {str(e)}")

    # ----------------
    # CRUD Operations
    # ----------------
    async def create_attendant(self, data:dict):
        try:
            exists = await self.find_by_login(data["login"])
            
            if exists: raise Exception("Attendant with this login already exists.")

            attendant = Attendant(**data)
            att_dict = attendant.to_dict()

            # Fix Enum serialization if necessary
            if "permission" in att_dict and hasattr(att_dict["permission"], "value"):
                att_dict["permission"] = att_dict["permission"].value
                
            result = await self._repository.save(att_dict)
            if result:
                await self.reset_users_cache()
            
            return result
        except Exception as e:
            raise Exception(f"Error creating attendant: {str(e)}")
            
    async def authenticate_attendant(self, login: str, password: str):
        # We need a method to find by login in repo
        attendant_data = await self.find_by_login(login)
        if not attendant_data:
            return None

        attendant = Attendant(**attendant_data)

        if not attendant.password_matches(password):
            return None
        
        return attendant_data
        
    async def create_token_for_attendant(self, attendant: dict):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": attendant["login"], "_id":attendant['_id'],"sector": attendant["sector"], "permission":attendant['permission']},
            expires_delta=access_token_expires
        )
        token = {"access_token": access_token, "token_type": "bearer"}
        self._cache.set("auth_token:", token)

        return token
    
    async def verify_token(self, token:str):
        try:
            token = self._cache.get(f"auth_token:{token}")
            if token:
                return True
            else:
                return False
        
        except Exception as e:
            raise ("Error during token verification: ", e)
    
    async def logout(self, token:dict):
        try:
            self._cache.delete(f"auth_token:{token}")
            return
        except Exception as e:
            raise ("Error during logout: ", e)
        
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
        