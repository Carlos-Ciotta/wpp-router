from repositories.contact import ContactRepository

class ContactService:
    def __init__(self, contact_repository):
        self._contact_repo:ContactRepository = contact_repository
    
    async def upsert_contact(self, phone: str, name: str, timestamp: int):
        """Cria ou atualiza um contato."""
        try:
            await self._contact_repo.update_contact(phone, name, timestamp)
        except Exception as e:
            print(f"Erro ao upsertar contato {phone}: {e}")