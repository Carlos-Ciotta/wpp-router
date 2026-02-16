"""Rotas para gerenciamento de sessões de chat."""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, Query
from typing import List, Optional
from core.dependencies import get_session_repository, get_chat_service
from services.chat_service import ChatService
from domain.session.chat_session import ChatSession, SessionStatus
from pydantic import BaseModel, Field
from core.websocket import manager
from datetime import datetime
from utils.auth import PermissionChecker

admin_permission = PermissionChecker(allowed_permissions=["admin"])
user_permission = PermissionChecker(allowed_permissions=["user", "admin"])

router = APIRouter(prefix="/sessions", tags=["Sessions"])

# --- Schemas ---
class SessionResponse(BaseModel):
    phone_number: str
    status: str
    created_at: float
    last_interaction_at: float
    last_client_interaction_at: Optional[float] = None
    attendant_id: Optional[str] = None
    category: Optional[str] = None
    _id: Optional[str] = None

    class Config:
        from_attributes = True

class StartSessionRequest(BaseModel):
    phone_number: str
    attendant_id: str
    category: str

class TransferSessionRequest(BaseModel):
    phone_number: str
    new_attendant_id: str

@router.post("/start", response_model=SessionResponse, status_code=201)
async def start_session(
    request: StartSessionRequest,
    token: str = Depends(user_permission),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Inicia manualmente uma nova sessão de atendimento.
    """
    try:
        session = await chat_service.start_chat(request.phone_number, request.attendant_id, request.category)
        return SessionResponse(**session.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transfer")
async def transfer_session(
    
    request: TransferSessionRequest,
    token: str = Depends(user_permission),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Transfere uma sessão ativa para outro atendente.
    """
    try:
        await chat_service.transfer_chat(request.phone_number, request.new_attendant_id)
        return {"message": "Atendimento transferido com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{phone_number}/finish")
async def finish_session(
    phone_number: str,
    token: str = Depends(user_permission),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Finaliza uma sessão ativa.
    """
    try:
        await chat_service.finish_session(phone_number)
        return {"message": "Sessão finalizada com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[SessionResponse])
async def get_all_sessions(
    chat_service: ChatService = Depends(get_chat_service),
    token: str = Depends(admin_permission),
):
    """
    Retorna a última sessão de cada cliente do sistema.
    """
    try:
        return await chat_service.list_sessions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

 # --------------
 # Websocket routes
 # --------------

@router.websocket("/ws/attendant/{attendant_id}", response_model=List[SessionResponse])
async def get_sessions_by_attendant(
    websocket: WebSocket,
    attendant_id: str = Query(..., description="ID do atendente"),
    token: str = Depends(user_permission),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Retorna a última sessão de cada cliente atendido por um atendente específico.
    """
    try:
        cursor = await chat_service.get_sessions_by_attendant(attendant_id)
        sessions = []
        async for doc in cursor:
            # O repositório pode retornar dict ou ChatSession. Garantimos a conversão.
            if isinstance(doc, dict):
                sessions.append(SessionResponse(**doc))
            elif isinstance(doc, ChatSession):
                sessions.append(SessionResponse(**doc.to_dict()))
            else:
                 # Caso venha do motor cursor diretamente como dict
                 sessions.append(SessionResponse(**doc))
                 
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))