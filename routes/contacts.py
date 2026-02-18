from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List
from domain.contact.contact import Contact
from repositories.contact import ContactRepository
from core.dependencies import get_contact_repository
from utils.auth import PermissionChecker

admin_permission = PermissionChecker(allowed_permissions=["admin"])
user_permission = PermissionChecker(allowed_permissions=["user", "admin"])


class ContactsRoutes():
    def __init__(self):
        self.router = APIRouter(prefix="/contacts", tags=["Contacts"])
        self._register_routes()

    def _register_routes(self):
        self.router.add_api_route("/", self.list_contacts, methods=["GET"], response_model=List[Contact])
        self.router.add_api_route("/{phone}", self.get_contact, methods=["GET"], response_model=Contact)

    async def list_contacts(
        self,
        limit: int = Query(50, le=100, description="Limite de contatos"),
        skip: int = 0,
        token: str = Depends(user_permission),
        repo: ContactRepository = Depends(get_contact_repository)
    ):
        """
        Lista contatos ordenados pela última mensagem recebida.
        """
        try:
            return await repo.list_contacts(limit, skip)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_contact(
        self,
        phone: str,
        token: str = Depends(user_permission),
        repo: ContactRepository = Depends(get_contact_repository)
    ):
        """
        Busca detalhes de um contato específico.
        """
        try:
            contact = await repo.get_by_phone(phone)
            if not contact:
                raise HTTPException(status_code=404, detail="Contato não encontrado")
            return contact
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


_routes = ContactsRoutes()
router = _routes.router
