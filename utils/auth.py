import jwt
import logging
from fastapi import HTTPException, status, Depends, Request, WebSocket
from typing import List, Optional
from core.environment import get_environment
from core.dependencies import get_chat_service # Injeção do seu serviço que tem o verify_token

env = get_environment()

# Logger para este módulo
logger = logging.getLogger(__name__)


class PermissionChecker:
    def __init__(self, allowed_permissions: List[str]):
        self.allowed_permissions = allowed_permissions
        logger.debug("PermissionChecker criado; allowed_permissions=%s", self.allowed_permissions)

    async def __call__(
        self,
        request: Optional[Request] = None,
        websocket: Optional[WebSocket] = None,
        service = Depends(get_chat_service) # Injeta o service para checar o cache
    ):
        logger.debug("Iniciando checagem de permissão; allowed_permissions=%s", self.allowed_permissions)

        # 1. Resolve qual token usar (Header ou Query string para WS/request)
        actual_token = None
        token_source = None

        # Preferência: Header Authorization (Bearer), senão query param 'token'
        auth_header = None
        query_token = None

        if websocket is not None:
            auth_header = websocket.headers.get("authorization")
            query_token = websocket.query_params.get("token")
        elif request is not None:
            auth_header = request.headers.get("authorization")
            query_token = request.query_params.get("token")

        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                actual_token = parts[1]
            else:
                actual_token = auth_header
            token_source = "header"
        elif query_token:
            actual_token = query_token
            token_source = "query"

        logger.debug("Token fonte resolvida: %s", token_source)
        
        if not actual_token:
            logger.warning("Token de autenticação ausente (nenhuma fonte fornecida)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Token de autenticação ausente"
            )

        # 2. VALIDAÇÃO DE LOGOUT (CACHE):
        # Verifica se o token ainda existe na "Whitelist" do seu cache/Redis
        is_active = await service.verify_token(actual_token)
        logger.debug("Verificação de whitelist/cache do token retornou: %s", is_active)
        if not is_active:
            logger.warning("Token inválido ou encerrado segundo cache/whitelist")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessão inválida ou encerrada"
            )

        try:
            # 3. Decodifica o JWT
            payload = jwt.decode(actual_token, env.SECRET_KEY, algorithms=[env.ALGORITHM])
            
            user_id = payload.get("_id")
            user_permission = payload.get("permission")
            logger.info("Token decodificado; user_id=%s, permission=%s", user_id, user_permission)

            # Validação de estrutura do payload
            if not user_id or not user_permission:
                logger.warning("Token com payload incompleto: %s", payload)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="Token com dados incompletos"
                )

            # 4. Verificação de Permissão (RBAC)
            # Permite acesso se a permissão estiver na lista ou se for admin
            if user_permission not in self.allowed_permissions and user_permission != "admin":
                logger.warning(
                    "Acesso negado; user_id=%s, permission=%s, required=%s",
                    user_id, user_permission, self.allowed_permissions
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Você não tem permissão para acessar este recurso"
                )

            logger.debug("Permissão concedida para user_id=%s", user_id)
            return payload 

        except jwt.ExpiredSignatureError as e:
            logger.warning("Token expirado: %s", str(e))
            raise HTTPException(status_code=401, detail="Token expirado")
        except jwt.PyJWTError as e:
            logger.exception("Erro ao validar/decodificar token: %s", str(e))
            raise HTTPException(status_code=401, detail="Token inválido")