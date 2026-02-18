from domain.attendants.attendant import Attendant
from repositories.attendant import AttendantRepository
from utils.security import Security
from datetime import datetime
from utils.cache import Cache
import json
from core.environment import get_environment

class AttendantService():
    def __init__(self, 
                 repository:AttendantRepository,
                 cache:Cache,
                 security:Security) -> None:
        self._repository = repository
        self._cache = cache
        self._security = security
        self._env = get_environment()

    # ----------------
    # Cache Helpers
    # ----------------
    async def _cache_attendant(self, user: dict):
        user_id = user["_id"]

        await self._cache.hset(
            f"attendant:{user_id}",
            mapping={
                "_id": user["_id"],
                "name": user["name"],
                "login": user["login"],
                "password": user["password"],
                "permission": user["permission"],
                "sector": json.dumps(user["sector"]),
                "clients": json.dumps(user["clients"]),
                "working_hours": json.dumps(user["working_hours"]),
            }
        )

        await self._cache.set(f"attendant:login:{user['login']}", user_id)

        for sector in user.get("sector", []):
            await self._cache.sadd(f"sector:{sector}", user_id)

        await self._cache.sadd(f"permission:{user['permission']}", user_id)

    # ----------------
    # Helpers
    # ----------------
    async def find_by_login(self, login: str):
        try:
            user_id = await self._cache.get(f"attendant:login:{login}")

            if user_id:
                return await self._cache.get(f"attendant:{user_id}")
            
            user = await self._repository.find_by_login(login)
            if not user:
                return None

            await self._cache_attendant(user)
            return user
        except Exception as e:
            raise Exception(f"Error finding attendant by login: {str(e)}")

    async def find_by_id(self, _id: str):
        try:
            user = await self._cache.get(f"attendant:{_id}")
            if user:
                return user
            
            user = await self._repository.find_by_id(_id)
            if not user:
                return None

            await self._cache_attendant(user)
            return user
        except Exception as e:
            raise Exception(f"Error finding attendant by ID: {str(e)}")
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
                await self._cache_attendant(result)
            
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
        
        return attendant.to_dict()
        
    async def create_token_for_attendant(self, attendant: dict):
        try:
            exists_token = await self._cache.get(f"auth_token:{attendant['_id']}")

            if exists_token:
                # `exists_token` may be bytes (old redis client) or str; normalize to str
                if isinstance(exists_token, (bytes, bytearray)):
                    token_str = exists_token.decode("utf-8")
                else:
                    token_str = str(exists_token)

                verified = await self._security.verify_token(token_str)
                return token_str if verified.get('_id') == attendant['_id'] else None
            
            if not attendant:
                raise Exception("Attendant not found for token creation.")
            
            access_token = self._security.create_token(
                payload={
                    "sub": attendant["login"],
                    "_id":attendant['_id'],
                    "permission":attendant['permission'],
                    "type":"access", 
                    "iat": datetime.now().timestamp(),
                    "exp": self._env.ACCESS_TOKEN_EXPIRE_SECONDS, 
                    "name": attendant["name"]}
            )
            # store token dict keyed by the access token so verify_token can lookup
            await self._cache.set(f"auth_token:{attendant['_id']}", access_token)

            return access_token
        
        except Exception as e:
            raise Exception(f"Error creating token for attendant: {str(e)}")
    
    async def logout(self, attendant_id:str):
        try:
            await self._cache.delete(f"auth_token:{attendant_id}")
            return
        except Exception as e:
            raise Exception(f"Error during logout: {e}")
        
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
        
