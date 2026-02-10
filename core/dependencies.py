from motor.motor_asyncio import AsyncIOMotorCollection

from core.settings import settings
from core.db import mongo_manager
from core.environment import get_environment
from repositories.message import MessageRepository
from client.whatsapp.V24 import WhatsAppClient
def get_settings():
	return settings


env = get_environment()

async def get_db_collection(collection_name: str) -> AsyncIOMotorCollection:
	"""Retorna uma coleção do MongoDB."""
	db = mongo_manager.get_db(db_name=env.DATABASE_NAME)
	return db[collection_name]

async def get_message_repository():
	"""Retorna uma instância do repositório de mensagens."""
	collection = await get_db_collection("messages")
	return MessageRepository(collection)
async def get_clients():
	"""Retorna todos os clients instanciados."""
	return {
		"whatsapp": WhatsAppClient(
			phone_id=env.WHATSAPP_PHONE_ID,
			wa_token=env.WHATSAPP_TOKEN,
			repository=await get_message_repository(),
			base_url=f"https://graph.facebook.com/v24.0/{env.WHATSAPP_PHONE_ID}/messages",
			internal_token=env.WHATSAPP_INTERNAL_TOKEN
		)
	}