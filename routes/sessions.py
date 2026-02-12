"""Rotas para gerenciamento de sessões de chat."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from repositories.session import SessionRepository
from core.dependencies import get_session_repository
from domain.session.chat_session import ChatSession, SessionStatus
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/sessions", tags=["Sessions"])

# --- Schemas ---
class SessionResponse(BaseModel):
    phone_number: str
    status: str
    created_at: datetime
    last_interaction_at: datetime
    attendant_id: Optional[str] = None
    category: Optional[str] = None
    _id: Optional[str] = None

    class Config:
        from_attributes = True

@router.get("/attendant/{attendant_id}", response_model=List[SessionResponse])
async def get_sessions_by_attendant(
    attendant_id: str,
    status: Optional[str] = Query(None, description="Filtrar por status: waiting_menu, active ou closed"),
    session_repo: SessionRepository = Depends(get_session_repository)
):
    """
    Retorna todas as sessões de um atendente específico.
    
    - **attendant_id**: ID do atendente
    - **status**: (Opcional) Filtrar por status da sessão
    """
    try:
        sessions = await session_repo.get_sessions_by_attendant(attendant_id, status)
        return [SessionResponse(**session.dict()) for session in sessions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/attendant/{attendant_id}/active", response_model=List[SessionResponse])
async def get_active_sessions_by_attendant(
    attendant_id: str,
    session_repo: SessionRepository = Depends(get_session_repository)
):
    """
    Retorna apenas as sessões ativas de um atendente específico.
    
    - **attendant_id**: ID do atendente
    """
    try:
        sessions = await session_repo.get_sessions_by_attendant(
            attendant_id, 
            status=SessionStatus.ACTIVE.value
        )
        return [SessionResponse(**session.dict()) for session in sessions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[SessionResponse])
async def get_all_sessions(
    status: Optional[str] = Query(None, description="Filtrar por status: waiting_menu, active ou closed"),
    limit: int = Query(100, description="Limite de resultados (máx: 500)", le=500),
    session_repo: SessionRepository = Depends(get_session_repository)
):
    """
    Retorna todas as sessões do sistema.
    
    - **status**: (Opcional) Filtrar por status da sessão
    - **limit**: Número máximo de resultados (padrão: 100, máximo: 500)
    """
    try:
        sessions = await session_repo.get_all_sessions(status, limit)
        return [SessionResponse(**session.dict()) for session in sessions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/phone/{phone_number}", response_model=Optional[SessionResponse])
async def get_session_by_phone(
    phone_number: str,
    session_repo: SessionRepository = Depends(get_session_repository)
):
    """
    Retorna a sessão ativa de um número de telefone específico.
    
    - **phone_number**: Número de telefone do cliente
    """
    try:
        session = await session_repo.get_active_session(phone_number)
        if not session:
            raise HTTPException(status_code=404, detail="Sessão ativa não encontrada")
        return SessionResponse(**session.dict())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
