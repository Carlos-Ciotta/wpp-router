from fastapi import APIRouter, Depends, HTTPException, status
from domain.config.chat_config import ChatConfig
from repositories.config import ConfigRepository
from core.dependencies import get_config_repository
from utils.auth import PermissionChecker

admin_permission = PermissionChecker(allowed_permissions=["admin"])
user_permission = PermissionChecker(allowed_permissions=["user", "admin"])


class ConfigRoutes():
    def __init__(self):
        self.router = APIRouter(prefix="/config", tags=["Configuration"])
        self._register_routes()

    def _register_routes(self):
        self.router.add_api_route("/", self.get_config, methods=["GET"], response_model=ChatConfig)
        self.router.add_api_route("/", self.update_config, methods=["POST"], response_model=ChatConfig)

    async def get_config(self,
        repo: ConfigRepository = Depends(get_config_repository),
        token: str = Depends(admin_permission),
    ):
        """
        Retorna a configuração atual do chat (mensagens, botões).
        """
        return await repo.get_config()

    async def update_config(self,
        config: ChatConfig,
        token: str = Depends(admin_permission),
        repo: ConfigRepository = Depends(get_config_repository)
    ):
        """
        Atualiza a configuração do chat.
        """
        return await repo.save_config(config)


_routes = ConfigRoutes()
router = _routes.router
