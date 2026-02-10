from motor.motor_asyncio import AsyncIOMotorCollection

from core.settings import settings
from core.db import mongo_manager
from core.environment import get_environment

from repositories.documents_repo import DocumentsRepository

from services.documents_service import DocumentService
from services.log_service import LogService

def get_settings():
	return settings


env = get_environment()

async def get_log_service() -> LogService:
	"""Provides a shared LogService instance for the application."""
	return LogService()

async def get_repositories():
	"""Retorna todos os repositories instanciados."""
	await mongo_manager.connect()
	
	return {
		"document": DocumentsRepository(mongo_manager.get_collection("documents")),
	}


async def get_services():
	"""Retorna todos os services instanciados."""
	repos = await get_repositories()
	log = await get_log_service()
	
	document_service = DocumentService(
		repository=repos["document"],
		logger=log
	)
	
	return {
		"document": document_service,
		"log": log,
	}