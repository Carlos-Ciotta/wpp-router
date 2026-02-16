from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List
from domain.contact.contact import Contact
from repositories.contact import ContactRepository
from core.dependencies import get_contact_repository
from utils.auth import PermissionChecker

admin_permission = PermissionChecker(allowed_roles=["admin"])
user_permission = PermissionChecker(allowed_roles=["user", "admin"])


router = APIRouter(prefix="/contacts", tags=["Contacts"])

@router.get("/", response_model=List[Contact])
async def list_contacts(
    limit: int = Query(50, le=100, description="Limite de contatos"),
    skip: int = 0,
    token: str = Depends(user_permission), # Both users and admins can list contacts
    repo: ContactRepository = Depends(get_contact_repository)
):
    """
    Lista contatos ordenados pela última mensagem recebida.
    """
    try:
        return await repo.list_contacts(limit, skip)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{phone}", response_model=Contact)
async def get_contact(
    phone: str,
    token: str = Depends(user_permission), # Both users and admins can list contacts
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
