import jwt
from fastapi import HTTPException, status, Depends, Query
from typing import List, Optional
from core.environment import get_environment
from core.dependencies import get_chat_service # Injeção do seu serviço que tem o verify_token

env = get_environment()

class PermissionChecker:
    def __init__(self, allowed_permissions: List[str]):
        self.allowed_permissions = allowed_permissions

    async def __call__(
        self, 
        token: Optional[str] = None, # Captura de dependências como OAuth2PasswordBearer se usado
        token_query: Optional[str] = Query(None, alias="token"),
        service = Depends(get_chat_service) # Injeta o service para checar o cache
    ):
        # 1. Resolve qual token usar (Header ou Query string para WS)
        actual_token = token or token_query
        
        if not actual_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Token de autenticação ausente"
            )

        # 2. VALIDAÇÃO DE LOGOUT (CACHE):
        # Verifica se o token ainda existe na "Whitelist" do seu cache/Redis
        is_active = await service.verify_token(actual_token)
        if not is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessão inválida ou encerrada"
            )

        try:
            # 3. Decodifica o JWT
            payload = jwt.decode(actual_token, env.SECRET_KEY, algorithms=[env.ALGORITHM])
            
            user_id = payload.get("_id")
            user_permission = payload.get("permission")

            # Validação de estrutura do payload
            if not user_id or not user_permission:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="Token com dados incompletos"
                )

            # 4. Verificação de Permissão (RBAC)
            # Permite acesso se a permissão estiver na lista ou se for admin
            if user_permission not in self.allowed_permissions and user_permission != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Você não tem permissão para acessar este recurso"
                )

            return payload 

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expirado")
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Token inválido")