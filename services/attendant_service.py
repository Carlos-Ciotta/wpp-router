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
            if self._cache.ensure():
                self._cache.delete("users")
                self._cache.set("users", self._repository.list())
        except Exception as e:
            raise ("Error during cache search: ", e)
    async def get_users_cached(self):
        try:
            if self._cache.ensure():
                yield self._cache.get("users")
            return
        except Exception as e:
            raise ("Error during cache search: ", e)
    # ----------------
    # Helpers
    # ----------------
    async def find_by_login(self, login: str):
        try:
            cached = self.get_users_cached()
            if cached:
                return cached.get("login") == login
            return await self._repository.find_by_login(login)
        except Exception as e:
            raise Exception(f"Error finding attendant by login: {str(e)}")
    # ----------------
    # CRUD Operations
    # ----------------
    async def create_attendant(self, data:dict):
        try:
            exists = self._find_by_login(data["login"])
            
            if exists: raise Exception("Attendant with this login already exists.")

            attendant = Attendant(**data)
            result= await self._repository.save(attendant.to_dict())
            if result:
                self._cache.delete("users")
                self.reset_users_cache()
        except Exception as e:
            raise Exception(f"Error creating attendant: {str(e)}")
            
    async def authenticate_attendant(self, login: str, password: str):
        # We need a method to find by login in repo
        attendant = await self.find_by_login(login)

        attendant = Attendant(**attendant)

        if not attendant:
            return None
        if not attendant.password_matches(password):
            return None
        
        return True
        
    async def create_token_for_attendant(self, attendant: dict):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": attendant["login"], "sector": attendant["sector"], "permission":attendant['permission']},
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
        