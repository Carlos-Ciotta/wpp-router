from motor.motor_asyncio import AsyncIOMotorCollection

from core.settings import settings
from core.db import mongo_manager
from core.environment import get_environment

from repositories.message import MessageRepository
from repositories.chat_repo import ChatRepository
from repositories.attendant import AttendantRepository
from repositories.config import ConfigRepository
from repositories.template import TemplateRepository
from repositories.contact import ContactRepository

from services.attendant_service import AttendantService
from services.chat_service import ChatService
from services.contact_service import ContactService
from services.message_service import MessageService

from client.whatsapp.V24 import WhatsAppClient
from utils.cache import Cache
from utils.security import Security

def get_settings():
	return settings


env = get_environment()


def get_db_collection(collection_name: str) -> AsyncIOMotorCollection:
	"""Retorna uma coleção do MongoDB."""
	db = mongo_manager.get_db(db_name=env.DATABASE_NAME)
	return db[collection_name]

def get_cache():
	"""Retorna uma instância do cache."""
	return Cache(env.REDIS_URL)

def get_repositories():
    """Retorna todas as instâncias dos repositórios."""
    return {
        "message_repository": MessageRepository(
            get_db_collection("messages")
        ),
        "chat_repository": ChatRepository(
            get_db_collection("chats")
        ),
        "attendant_repository": AttendantRepository(
            get_db_collection("attendants")
        ),
        "config_repository": ConfigRepository(
            get_db_collection("configs")
        ),
        "template_repository": TemplateRepository(
            get_db_collection("templates")
        ),
        "contact_repository": ContactRepository(
            get_db_collection("contacts")
        )
    }

async def get_security():
    """Retorna uma instância do Security."""
    return Security()

def get_clients():
	"""Retorna todos os clients instanciados."""
	return {
		"whatsapp": WhatsAppClient(
			phone_id=env.WHATSAPP_PHONE_ID,
			business_account_id=env.WHATSAPP_BUSINESS_ACCOUNT_ID,
			wa_token=env.WHATSAPP_TOKEN,
			repository=get_repositories()["config_repository"],
			base_url="https://graph.facebook.com/v24.0",
			internal_token=env.WHATSAPP_INTERNAL_TOKEN
		)
	}
def get_attendant_service():
    """Retorna uma instância do AttendantService."""
    return AttendantService(
        attendant_repo=(get_repositories())["attendant_repository"],
        cache=get_cache()
    )
def get_contact_service():
    """Retorna uma instância do ContactService."""
    return ContactService(
        contact_repo=(get_repositories())["contact_repository"],
        cache=get_cache(),
        security=get_security()
    )
def get_chat_service():
    """Retorna chat service"""
    return ChatService(
            wa_client=(get_clients())["whatsapp"],
			chat_repo= (get_repositories())["chat_repository"],
			template_repo= (get_repositories())["template_repository"],
			config_repo= (get_repositories())["config_repository"],
			attendant_service=get_attendant_service(),
            contact_service=get_contact_service(),
            cache=get_cache()
    )

def get_message_service():
    """Retorna message service"""
    return MessageService(
        message_repo=(get_repositories())["message_repository"],
        chat_service=get_chat_service(),
        cache=get_cache()
    )