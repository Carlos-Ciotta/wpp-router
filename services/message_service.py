from repositories.message import MessageRepository
import logging

class MessageService:
    def __init__(self, message_repository:MessageRepository):
        self._message_repo = message_repository

    async def get_messages_by_phone(self, 
                                    phone: str, 
                                    limit: int = 50, 
                                    skip: int = 0):
        
        return [m async for m in self._message_repo.get_messages_by_phone_number(phone, limit, skip)]

    async def get_history(self, 
                          phone: str, 
                          last_timestamp: str, 
                          limit: int = 50):
        """Retorna histórico anterior ao timestamp fornecido."""
        return [m async for m in self._message_repo.get_messages_before(phone, last_timestamp, limit)]

    async def stream_new_messages(self, phone: str):
        """Repassa o gerador do repository para quem chamar."""
        async for message in self._message_repo.watch_new_messages(phone):
            yield message