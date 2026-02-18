
from core.environment import get_environment
from fastapi import HTTPException
from jose import jwt,JWTError

class Security():
    def __init__(self):
        self._env = get_environment()
    
    async def create_token(self,
                        payload: dict) -> str:
        try:
            token = jwt.encode(payload, self._env.SECRET_KEY, algorithm=self._env.ALGORITHM)
            return token
        except Exception as e:
            print(f"Erro ao criar token: {e}")
            raise e
        
    async def verify_token(self,
                           token: str) -> bool:
        try:
            # Decodifica e verifica assinatura, expiração (exp) e not before (nbf)
            decoded = jwt.decode(token, self._env.SECRET_KEY, algorithms=self._env.ALGORITHM)
            
            print("Token é válido!")

            return decoded
        
        except JWTError as e:
            # Captura erros de assinatura inválida, token expirado, etc.
            print("Token inválido:", str(e))
            raise HTTPException(401, "Invalid Token")
        except Exception as e:
            print("Erro inesperado:", str(e))
            return HTTPException(500, "Internal Server Error")

    async def verify_permission(self,
                                token: str,
                                allowed_permissions: list) -> bool:
        try:
            decoded = await self.verify_token(token)
            if not decoded:
                return False
            
            permission = decoded.get("permission")
            if permission in allowed_permissions:
                return True
            else:
                print(f"Permissão '{permission}' não é suficiente. Permissões permitidas: {allowed_permissions}")
                raise HTTPException(401, "Lack of permission")
            
        except JWTError as e:
            # Captura erros de assinatura inválida, token expirado, etc.
            print("Token inválido:", str(e))
            raise HTTPException(401, "Invalid Token")
        except Exception as e:
            print("Erro inesperado:", str(e))
            return HTTPException(500, "Internal Server Error")