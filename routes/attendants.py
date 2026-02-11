from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from domain.attendants.attendant import Attendant
from services.attendant_service import AttendantService
from services.chat_service import ChatService
from core.dependencies import get_attendant_service, get_chat_service
from typing import List

router = APIRouter(prefix="/attendants", tags=["Attendants"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="attendants/login")

@router.post("/transfer")
async def transfer_chat(
    client_phone: str = Body(..., embed=True),
    target_attendant_id: str = Body(..., embed=True),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Transfere um cliente para outro atendente.
    """
    try:
        result = await chat_service.transfer_attendant(client_phone, target_attendant_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/finish")
async def finish_session(
    client_phone: str = Body(..., embed=True),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Finaliza a sessão (marca como não ativa).
    """
    try:
        return await chat_service.finish_session(client_phone)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reopen")
async def reopen_session(
    client_phone: str = Body(..., embed=True),
    attendant_id: str = Body(..., embed=True),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Reabre chat (ou cria novo) e atribui ao atendente.
    """
    try:
        return await chat_service.reopen_session(client_phone, attendant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_attendant(
    attendant: Attendant, 
    service: AttendantService = Depends(get_attendant_service)
):
    """
    Cria um novo atendente.
    """
    # Verify if login already exists? The service assumes repo save is enough, but unique index would be better.
    # For now, we trust the repo/service flow.
    result = await service.create_attendant(attendant.model_dump())
    return {"id": str(result), "message": "Attendant created successfully"}

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AttendantService = Depends(get_attendant_service)
):
    """
    Realiza login e retorna token JWT.
    """
    attendant = await service.authenticate_attendant(form_data.username, form_data.password)
    if not attendant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return await service.create_token_for_attendant(attendant)

@router.get("/", response_model=List[dict])
async def list_attendants(
    service: AttendantService = Depends(get_attendant_service)
    # Could add token dependency here to secure listing
):
    """
    Lista todos os atendentes.
    """
    attendants = await service.list_attendants()
    # Convert ObjectId to str for response
    for att in attendants:
        if "_id" in att:
            att["_id"] = str(att["_id"])
    return attendants
