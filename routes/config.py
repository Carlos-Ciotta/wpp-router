from fastapi import APIRouter, Depends, status, Body
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from domain.config.chat_config import ChatConfig
from core.dependencies import get_config_service, get_security

fastapi_security = HTTPBearer()

class ConfigRoutes():
    def __init__(self):
        self.router = APIRouter(prefix="/config", tags=["Configuration"])
        self._security = get_security()
        self._config_service = get_config_service()
        self._register_routes()

    def _register_routes(self):
        self.router.add_api_route("/", self.get_config, methods=["GET"], response_model=ChatConfig, status_code=status.HTTP_200_OK)
        self.router.add_api_route("/", self.update_config, methods=["POST"], response_model=ChatConfig, status_code=status.HTTP_200_OK)

    async def get_config(self,
        token: HTTPAuthorizationCredentials = Depends(fastapi_security),
    ):
        """
        Retorna a configuração atual do chat (mensagens, botões).
        """
        self._security.verify_permission(token.credentials, ["user", "admin"])
        
        return self._config_service.get_config()

    async def update_config(self,
        config: ChatConfig = Body(...),
        token: HTTPAuthorizationCredentials = Depends(fastapi_security),
    ):
        """
        Atualiza a configuração do chat.
        """
        self._security.verify_permission(token.credentials, ["user", "admin"])
        
        return self._config_service.save_config(config)


_routes = ConfigRoutes()
router = _routes.router
