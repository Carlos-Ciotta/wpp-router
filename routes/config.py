from fastapi import APIRouter, Depends, HTTPException, status
from domain.config.chat_config import ChatConfig
from repositories.config import ConfigRepository
from core.dependencies import get_config_repository
from utils.auth import PermissionChecker

admin_permission = PermissionChecker(allowed_roles=["admin"])
user_permission = PermissionChecker(allowed_roles=["user", "admin"])

router = APIRouter(prefix="/config", tags=["Configuration"])

@router.get("/", response_model=ChatConfig)
async def get_config(
    repo: ConfigRepository = Depends(get_config_repository),
    token: str = Depends(admin_permission),
):
    """
    Retorna a configuração atual do chat (mensagens, botões).
    """
    return await repo.get_config()

@router.post("/", response_model=ChatConfig)
async def update_config(
    config: ChatConfig,
    token: str = Depends(admin_permission),
    repo: ConfigRepository = Depends(get_config_repository)
):
    """
    Atualiza a configuração do chat.
    """
    return await repo.save_config(config)
