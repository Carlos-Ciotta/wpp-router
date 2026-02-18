from repositories.contact import ContactRepository

class ContactService:
    def __init__(self, contact_repository):
        self._contact_repo:ContactRepository = contact_repository
    
    async def upsert_contact(self, phone: str, name: str, timestamp: int):
        """Cria ou atualiza um contato."""
        try:
            await self._contact_repo.update_contact(phone, name, timestamp)
            # Return the stored contact for callers that expect the upsert result
            return await self._contact_repo.get_by_phone(phone)
        except Exception as e:
            print(f"Erro ao upsertar contato {phone}: {e}")

    async def list_contacts(self, limit: int = 300, skip: int = 0):
        """Lista contatos ordenados pela última mensagem recebida."""
        try:
            return await self._contact_repo.list_contacts(limit, skip)
        except Exception as e:
            print(f"Erro ao listar contatos: {e}")
            raise e
        
    async def get_by_phone(self, phone: str):
        """Busca detalhes de um contato específico."""
        try:
            return await self._contact_repo.get_by_phone(phone)
        except Exception as e:
            print(f"Erro ao buscar contato {phone}: {e}")
            raise e
        
    async def delete_contact(self, phone: str):
        """Deleta um contato."""
        try:
            await self._contact_repo.delete_contact(phone)
        except Exception as e:
            print(f"Erro ao deletar contato {phone}: {e}")