from motor.motor_asyncio import AsyncIOMotorCollection

from core.settings import settings
from core.db import mongo_manager
from core.environment import get_environment

from client.whatsapp.V24 import WhatsAppClient

def get_settings():
	return settings


env = get_environment()


async def get_clients():
	"""Retorna todos os clients instanciados."""
	return {
		"whatsapp": WhatsAppClient(
			phone_id=env.WHATSAPP_PHONE_ID,
			wa_token=env.WHATSAPP_TOKEN,
			base_url=f"https://graph.facebook.com/v24.0/{env.WHATSAPP_PHONE_ID}/messages",
			internal_token=env.WHATSAPP_INTERNAL_TOKEN
		)
	}