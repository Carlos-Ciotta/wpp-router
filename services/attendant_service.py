from domain.attendants.attendant import Attendant
from fastapi import HTTPException
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
                "_id": str(user["_id"]),
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
            # Se não for erro de negócio, lançamos 500 explicitamente ou deixamos subir
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

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
            # Ajustado para HTTPException 500
            raise HTTPException(status_code=500, detail=f"Error finding attendant by ID: {str(e)}")
    # ----------------
    # CRUD Operations
    # ----------------
    async def create_attendant(self, data: dict):
        exists = await self.find_by_login(data["login"])
        if exists: 
            # 409 Conflict é o mais adequado para duplicidade
            raise HTTPException(status_code=409, detail="Attendant with this login already exists.")

        try:
            attendant = Attendant(**data)
            att_dict = attendant.to_dict()

            if "permission" in att_dict and hasattr(att_dict["permission"], "value"):
                att_dict["permission"] = att_dict["permission"].value
                
            result = await self._repository.save(att_dict)
            if result:
                await self._cache_attendant(result)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creating attendant: {str(e)}")
            
    async def authenticate_attendant(self, login: str, password: str):
        # We need a method to find by login in repo
        attendant_data = await self.find_by_login(login)
        
        if not attendant_data:
            return None

        attendant = Attendant(**attendant_data)

        if not attendant.password_matches(password):
            return None
        
        return attendant.to_dict()
    async def get_by_clients_and_sector(self, phone: str, sector_name: str):
        try:
            # 1. Tenta encontrar atendente vinculado diretamente
            attendant = await self._repository.find_by_client_and_sector(phone, sector_name)
            if attendant:
                return attendant
            
            # 2. Se não encontrar, tenta por setor
            attendants_in_sector = await self._repository.find_by_sector(sector_name)
            if attendants_in_sector:
                return attendants_in_sector[0]  # Retorna o primeiro encontrado (pode ser melhorado com round-robin ou outro critério)

            return None
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error finding attendant by clients and sector: {str(e)}")
    async def create_token_for_attendant(self, attendant: dict):
        # 1. Tentar recuperar token do cache
        exists_token = await self._cache.get(f"auth_token:{attendant['_id']}")

        if exists_token:
            token_str = exists_token.decode("utf-8") if isinstance(exists_token, (bytes, bytearray)) else str(exists_token)
            
            try:
                # Se o token for inválido, o Security lançará HTTPException(401)
                verified = await self._security.verify_token(token_str)
                if verified.get('_id') == attendant['_id']:
                    return token_str
            except HTTPException:
                # Se o token do cache expirou/falhou, apenas ignoramos e geramos um novo
                pass

        if not attendant:
            raise HTTPException(status_code=404, detail="Attendant not found.")

        # 2. Gerar novo token
        try:
            # exp must be a future timestamp (current time + TTL)
            exp_ts = datetime.now().timestamp() + int(self._env.ACCESS_TOKEN_EXPIRE_SECONDS)
            access_token = await self._security.create_token(
                payload={
                    "sub": attendant["login"],
                    "_id": str(attendant['_id']),
                    "permission": attendant['permission'],
                    "type": "access",
                    "iat": datetime.now().timestamp(),
                    "exp": exp_ts,
                    "name": attendant["name"]
                }
            )
            await self._cache.set(f"auth_token:{str(attendant['_id'])}", access_token)
            return access_token
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Token generation failed: {str(e)}")
    
    async def logout(self, attendant_id: str):
        try:
            await self._cache.delete(f"auth_token:{str(attendant_id)}")
            return {"message": "Logout successful"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")
        
    async def update_attendant(self, _id: str, data: dict):
        try:
            result = await self._repository.update(_id, data)
            if not result:
                raise HTTPException(status_code=404, detail="Attendant not found for update.")
            
            # Opcional: Atualizar o cache após o update
            # await self._cache_attendant(result) 
            
            return result
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error updating attendant: {str(e)}")
        
    async def list_attendants(self, filter: dict = None):
        try:
            return await self._repository.list(filter)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error listing attendants: {str(e)}")
        
    async def delete_attendant(self, _id: str):
        try:
            result = await self._repository.delete(_id)
            if not result:
                raise HTTPException(status_code=404, detail="Attendant not found for deletion.")
            
            # Limpar cache após deletar
            await self._cache.delete(f"attendant:{_id}")
            
            return result
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting attendant: {str(e)}")
        
