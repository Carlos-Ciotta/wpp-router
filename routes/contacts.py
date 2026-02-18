from fastapi import APIRouter, Depends, Query, HTTPException, status, Body
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import List
from domain.contact.contact import Contact
from core.dependencies import get_contact_service, get_security

fastapi_security = HTTPBearer()

class ContactsRoutes():
    def __init__(self):
        self.router = APIRouter(prefix="/contacts", tags=["Contacts"])
        # avoid calling dependency factories at import time
        self._contact_service = None
        self._security = None
        self._register_routes()

    def _register_routes(self):
        self.router.add_api_route("/", self.list_contacts, methods=["GET"], response_model=List[Contact], status_code=status.HTTP_200_OK)
        self.router.add_api_route("/", self.get_contact, methods=["GET"], response_model=Contact, status_code=status.HTTP_200_OK)
        self.router.add_api_route("/delete", self.delete_contact, methods=["DELETE"], status_code=status.HTTP_200_OK)
        self.router.add_api_route("/register", self.create_contact, methods=["POST"], status_code=status.HTTP_200_OK)
    
    async def list_contacts(
        self,
        limit: int = Query(default=300, description="Limite de contatos"),
        skip: int = Query(default=0, description="Número de contatos a pular"),
        token: HTTPAuthorizationCredentials = Depends(fastapi_security),
    ):
        """
        Lista contatos ordenados pela última mensagem recebida.
        """
        try:
            security = get_security()
            contact_service = get_contact_service()
            await security.verify_permission(token.credentials, ["user", "admin"])
            return await contact_service.list_contacts(limit, skip)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_contact(
        self,
        phone: str = Query(..., description="Número de telefone do contato"),
        token: HTTPAuthorizationCredentials = Depends(fastapi_security),
    ):
        """
        Busca detalhes de um contato específico.
        """
        try:
            security = get_security()
            contact_service = get_contact_service()
            await security.verify_permission(token.credentials, ["user", "admin"])
            contact = await contact_service.get_by_phone(phone)
            if not contact:
                raise HTTPException(status_code=404, detail="Contato não encontrado")
            return contact
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_contact(
        self,
        phone: str = Query(..., description="Número de telefone do contato a ser deletado"),
        token: HTTPAuthorizationCredentials = Depends(fastapi_security),
    ):
        """
        Deleta um contato.
        """
        try:
            security = get_security()
            contact_service = get_contact_service()
            await security.verify_permission(token.credentials, ["admin"])
            await contact_service.delete_contact(phone)
            return {"message": "Contato deletado com sucesso"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    async def create_contact(
            self,
            contact: Contact = Body(...),
            token: HTTPAuthorizationCredentials = Depends(fastapi_security),
    ):
        """
        Registra um novo contato.
        """
        try:
            security = get_security()
            contact_service = get_contact_service()
            await security.verify_permission(token.credentials, ["admin"])
            result = await contact_service.upsert_contact(contact.model_dump())
            return {"id": str(result), "message": "Contato criado com sucesso"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
_routes = ContactsRoutes()
router = _routes.router
