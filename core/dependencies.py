from motor.motor_asyncio import AsyncIOMotorCollection

from core.settings import settings
from core.db import mongo_manager
from core.environment import get_environment
from repositories.message import MessageRepository
from repositories.session import SessionRepository
from repositories.attendant import AttendantRepository
from repositories.config import ConfigRepository
from repositories.template import TemplateRepository
from repositories.contact import ContactRepository
from services.attendant_service import AttendantService
from client.whatsapp.V24 import WhatsAppClient
from utils.cache import Cache

def get_settings():
	return settings


env = get_environment()

async def get_db_collection(collection_name: str) -> AsyncIOMotorCollection:
	"""Retorna uma coleção do MongoDB."""
	db = mongo_manager.get_db(db_name=env.DATABASE_NAME)
	return db[collection_name]

async def get_cache():
	"""Retorna uma instância do cache."""
	return Cache(env.REDIS_URL)

async def get_message_repository():
	"""Retorna uma instância do repositório de mensagens."""
	collection = await get_db_collection("messages")
	return MessageRepository(collection)

async def get_session_repository():
    collection = await get_db_collection("sessions")
    return SessionRepository(collection)

async def get_attendant_repository():
    collection = await get_db_collection("attendants")
    return AttendantRepository(collection)

async def get_attendant_service():
    repo = await get_attendant_repository()
    cache = await get_cache()
    return AttendantService(repo, cache)

async def get_config_repository():
    collection = await get_db_collection("configs")
    return ConfigRepository(collection)

async def get_template_repository():
    collection = await get_db_collection("templates")
    return TemplateRepository(collection)

async def get_contact_repository():
    collection = await get_db_collection("contacts")
    return ContactRepository(collection)

async def get_clients():
	"""Retorna todos os clients instanciados."""
	return {
		"whatsapp": WhatsAppClient(
			phone_id=env.WHATSAPP_PHONE_ID,
			business_account_id=env.WHATSAPP_BUSINESS_ACCOUNT_ID,
			wa_token=env.WHATSAPP_TOKEN,
			repository=await get_message_repository(),
			base_url="https://graph.facebook.com/v24.0",
			internal_token=env.WHATSAPP_INTERNAL_TOKEN
		)
	}
from services.chat_service import ChatService
async def get_chat_service():
    clients = await get_clients()
    wa_client = clients["whatsapp"]
    session_repo = await get_session_repository()
    attendant_repo = await get_attendant_repository()
    config_repo = await get_config_repository()
    template_repo = await get_template_repository()
    contact_repo = await get_contact_repository()
    message_repo = await get_message_repository()
    return ChatService(wa_client, 
                       session_repo, 
                       attendant_repo, 
                       config_repo, 
                       template_repo, 
                       contact_repo,
                       message_repo=message_repo, 
                       cache=await get_cache())

# core/dependencies.py (Parte HTTP)
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.auth_core import verify_token_payload
from core.dependencies import get_attendant_service # Sua injeção do serviço
from services.attendant_service import AttendantService

security_scheme = HTTPBearer()

async def get_current_user(
    token_auth: HTTPAuthorizationCredentials = Depends(security_scheme),
    service: AttendantService = Depends(get_attendant_service)
) -> dict:
    """
    Dependência para rotas HTTP/REST.
    Lança 401 se falhar.
    """
    token = token_auth.credentials # O FastAPI já remove o "Bearer " aqui

    try:
        payload = await verify_token_payload(token, service)
        return payload
    except ValueError as e:
        # HTTP precisa retornar Exception
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

# Factory para permissões (RBAC)
class RequirePermission:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, user: dict = Depends(get_current_user)):
        if user.get("permission") not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado"
            )
        return user
    
from fastapi import WebSocket, status, Query
from core.auth_core import verify_token_payload

async def get_ws_user(
    websocket: WebSocket,
    token: str = Query(..., description="Token JWT via query param"),
    service: AttendantService = Depends(get_attendant_service)
) -> dict:
    """
    Dependência exclusiva para WebSocket.
    Se falhar, não lança erro HTTP, mas retorna None ou fecha conexão.
    """
    try:
        # Tenta validar
        payload = await verify_token_payload(token, service)
        return payload
    except ValueError as e:
        # Em WebSocket, a dependência não deve fechar o socket diretamente
        # se usada no header da função, mas lançar HTTPException causa erro 403 no handshake.
        # A melhor prática é lançar HTTPException 403, que o FastAPI converte em recusa de conexão.
        print(f"WS Auth Error: {e}")
        raise HTTPException(status_code=403, detail=str(e))