from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
import logging
from fastapi import HTTPException, status, Depends, Request, WebSocket
from typing import List
from core.environment import get_environment
from core import security as core_security
from core.dependencies import get_attendant_service # Injeção do seu serviço que tem o verify_token

env = get_environment()

# Logger para este módulo
logger = logging.getLogger(__name__)


class PermissionChecker:
    def __init__(self, allowed_permissions: List[str]):
        self.allowed_permissions = allowed_permissions
        logger.debug("PermissionChecker criado; allowed_permissions=%s", self.allowed_permissions)

    async def __call__(
        self,
        request: Request = None,
        websocket: WebSocket = None,
        service = Depends(get_attendant_service)  # Injeta o service para checar o cache
    ):
        logger.debug("Iniciando checagem de permissão; allowed_permissions=%s", self.allowed_permissions)
        # 1. Resolve token (header ou query)
        headers = websocket.headers if websocket else request.headers
        query = websocket.query_params if websocket else request.query_params

        auth = headers.get("authorization")
        token = (
            auth.split()[1] if auth and auth.lower().startswith("bearer ")
            else auth or query.get("token")
        )

        if not token:
            raise HTTPException(401, "Token ausente")

        try:
            # 2. Decode JWT (use same key/algorithm as token creation)
            payload = jwt.decode(token, core_security.SECRET_KEY, algorithms=[core_security.ALGORITHM])
            attendant_id = payload.get("_id")
            permission = payload.get("permission")

            print(f'permission {permission}')
            if not attendant_id or not permission:
                raise HTTPException(401, "Token inválido")
            print ('passed decode, now checking cache/whitelist')
            # 3. Verifica whitelist/cache
            if not await service.verify_token(token, attendant_id):
                raise HTTPException(401, "Sessão inválida")
            print('passed cache/whitelist check')
            # 4. RBAC
            if permission not in self.allowed_permissions:
                raise HTTPException(403, "Permissão negada")

            return payload

        except ExpiredSignatureError:
            raise HTTPException(401, "Token expirado")
        except JWTError:
            raise HTTPException(401, "Token inválido")
