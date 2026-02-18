"""Rotas para gerenciamento de sessões de chat."""
from fastapi import APIRouter, HTTPException, WebSocket, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from typing import List, Optional
import json

from core.websocket import manager
from core.dependencies import get_chat_service, get_security
import logging

# --- Schemas ---
class ChatResponse(BaseModel):
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

class StartChatRequest(BaseModel):
    phone_number: str
    attendant_id: str
    category: str

class TransferChatRequest(BaseModel):
    phone_number: str
    new_attendant_id: str

fastapi_security = HTTPBearer()
class ChatRoutes():
    def __init__(self):
        # avoid calling dependency factories at import time
        self._chat_service = None
        self._security = None
        self.router = APIRouter(prefix="/chat", tags=["Chats"])
        self._register_routes()

    def _register_routes(self):
        self.router.add_api_route("/start", self.start_chat, methods=["POST"], status_code=201)
        self.router.add_api_route("/transfer", self.transfer_chat, methods=["POST"], status_code=200)
        self.router.add_api_route("/finish", self.finish_chat, methods=["POST"], status_code=200)
        self.router.add_api_route("/", self.get_all_chats, methods=["GET"], status_code=200)
        self.router.websocket("/ws/attendant", self.get_by_attendant_ws)
        self.router.websocket("/ws/admin", self.get_all_chats_ws)

        
    async def start_chat(self,
                            payload: StartChatRequest,
                            token:HTTPAuthorizationCredentials = Depends(fastapi_security)) -> dict:
        """Start a new chat chat, must containt phone number of client. Permission: user or admin.
            It also can reopen a closed chat"""
        
        try:
            security = get_security()
            chat_service = get_chat_service()
            await security.verify_permission(token.credentials, ["user", "admin"])
            chat = await chat_service.start_chat(payload.phone_number, payload.attendant_id, payload.category)
            return {"message": "Sessão iniciada com sucesso", "chat": chat, 
                "free_message":bool(chat_service.can_send_free_message(payload.phone_number))}
        
        except ValueError as e:
            raise HTTPException(400, "Input invalid")
        except Exception as e:
            raise HTTPException(500, "Internal Server Error")
        
    async def transfer_chat(self,
                                payload: TransferChatRequest,
                                token:HTTPAuthorizationCredentials = Depends(fastapi_security))->dict:
        """Transfer an active chat to another attendant. Permission: user or admin."""
        
        try:
            security = get_security()
            chat_service = get_chat_service()
            await security.verify_permission(token.credentials, ["user", "admin"])
            await chat_service.transfer_chat(payload.phone_number, payload.new_attendant_id)
            return {"message": "Atendimento transferido com sucesso", 
                "free_message":bool(chat_service.can_send_free_message(payload.phone_number))}
        
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(500, str(e))

    async def finish_chat(self,
                            phone_number: str = Query(..., description="Phone number of the client whose chat will be finished"),
                            token:HTTPAuthorizationCredentials = Depends(fastapi_security))->dict:
            """Finish an active chat. Permission: user or admin."""
            
            try:
                security = get_security()
                chat_service = get_chat_service()
                await security.verify_permission(token.credentials, ["user", "admin"])
                await chat_service.finish_chat(phone_number)
                return {"message": "Sessão finalizada com sucesso"}
            
            except ValueError as e:
                raise HTTPException(400, str(e))
            except Exception as e:
                raise HTTPException(500, str(e))

    async def get_all_chats(self,
                            token:HTTPAuthorizationCredentials = Depends(fastapi_security))->List[dict]:
        """Get the last chat of each client in the system. Permission: admin."""
        try:
            security = get_security()
            chat_service = get_chat_service()
            await security.verify_permission(token.credentials, ["admin"])
            return await chat_service.list_chats()
        
        except Exception as e:
            raise HTTPException(500, str(e))

    async def get_all_chats_ws(self,
                                  websocket: WebSocket):
        """Websocket endpoint to get the last chat of each client in the system. Permission: admin."""
        # Injetamos o serviço manualmente pois Depends não funciona dentro do while True
        await websocket.accept()

        auth_header = websocket.headers.get("authorization")

        # Fallback: some clients/browsers não permitem enviar headers no handshake.
        # Neste caso aceitaremos `?token=<token>` como alternativa para autenticação.
        token = None
        if auth_header:
            token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else auth_header
        else:
            token = websocket.query_params.get("token")

        if not token:
            await websocket.close(code=1008) # Policy Violation
            return None
        try:
            # Resolve dependencies at runtime for websocket
            security = get_security()
            chat_service = get_chat_service()
            # 4. Validar o token (usando a string limpa)
            decoded = await security.verify_permission(token, required_roles=["admin"])
            attendant_id = decoded.get("_id")
            
        except Exception as e:
            logging.exception("WebSocket auth failure")
            # Se o token for inválido ou não tiver permissão
            try:
                await websocket.send_json({"type": "error", "message": "Unauthorized"})
            except Exception:
                pass
            await websocket.close(code=1008)
            return None
        
        if not token:
            await websocket.close(code=1008)
            return None
        await manager.connect(attendant_id, websocket)
        try: 
            while True:
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)
                
                action = data.get("action") # ex: "get_chats", "update_chat"

                try:
                    result = await chat_service.list_chats()

                    response = {
                        "type": "success",
                        "action": action,
                        "data": result
                    }

                    await manager.send_personal_message(response, attendant_id)

                except Exception as e:
                    await manager.send_personal_message({
                        "type": "error",
                        "action": action,
                        "message": str(e)
                    }, attendant_id)

                    manager.disconnect(attendant_id)
                    break
        except Exception as e:
            manager.disconnect(attendant_id)
        
    async def get_by_attendant_ws(self,
                                  websocket: WebSocket):
        """Websocket endpoint to get the last chat of each client attended by a specific attendant. Permission: user or admin."""
        await websocket.accept()

        auth_header = websocket.headers.get("authorization")

        if not auth_header:
            await websocket.close(code=1008) # Policy Violation
            return None
        try:
            # Resolve dependencies at runtime for websocket
            security = get_security()
            chat_service = get_chat_service()

            # 3. Aceita token via header ou query-param (já normalizado acima)
            decoded = await security.verify_permission(token, required_roles=["admin"])
            attendant_id = decoded.get("_id")
            
        except Exception as e:
            logging.exception("WebSocket auth failure")
            try:
                await websocket.send_json({"type": "error", "message": "Unauthorized"})
            except Exception:
                pass
            await websocket.close(code=1008)
            return None
        
        if not token:
            await websocket.close(code=1008)
            return None
        await manager.connect(attendant_id, websocket)

        try:
            while True:
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)
                
                action = data.get("action") # ex: "get_chats", "update_chat"

                try:
                    result = await chat_service.get_chats_by_attendant(attendant_id)

                    response = {
                        "type": "success",
                        "action": action,
                        "data": result
                    }

                    await manager.send_personal_message(response, attendant_id)

                except Exception as e:
                    await manager.send_personal_message({
                        "type": "error",
                        "action": action,
                        "message": str(e)
                    }, attendant_id)

                    manager.disconnect(attendant_id)
                    break
        except Exception as e:
            manager.disconnect(attendant_id)

_routes = ChatRoutes()
router = _routes.router