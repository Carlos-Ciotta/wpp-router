from repositories.message import MessageRepository
class MessageService:
    def __init__(self, message_repository):
        self._message_repo = message_repository

    async def get_messages_by_phone(self, phone: str, limit: int = 50, skip: int = 0):
        """Busca mensagens de uma sessão específica."""
        try:
            return [m async for m in self._message_repo.get_messages_by_phone_number(phone, limit, skip)]
        except Exception as e:
            logging.error(f"Erro ao buscar mensagens para {phone}: {e}")
            return []