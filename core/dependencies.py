from motor.motor_asyncio import AsyncIOMotorCollection

from core.settings import settings
from core.db import mongo_manager
from core.environment import get_environment
from repositories.message import MessageRepository
from repositories.session import SessionRepository
from repositories.attendant import AttendantRepository
from repositories.config import ConfigRepository
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
    return AttendantService(repo)

async def get_config_repository():
    collection = await get_db_collection("configs")
    return ConfigRepository(collection)

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
    return ChatService(wa_client, session_repo, attendant_repo, config_repo, cache=await get_cache())