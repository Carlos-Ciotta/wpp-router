from fastapi import APIRouter, WebSocket
from core.dependencies import get_message_service, get_security
import json
from core.websocket import manager

class MessagesRoutes():
    def __init__(self):
        self.router = APIRouter(prefix="/messages")
        # avoid calling dependency factories at import time
        self._security = None
        self._message_service = None
        self._register_routes()

    def _register_routes(self):
        # Register websocket route
        self.router.websocket("/ws", self.get_message_by_phone_ws)

    async def get_message_by_phone_ws(self,
                                  websocket: WebSocket):
        """Websocket endpoint to get the last chat of each client in the system. Permission: admin."""
        # Injetamos o serviço manualmente pois Depends não funciona dentro do while True
        await websocket.accept()

        auth_header = websocket.headers.get("authorization")
        print(f"DEBUG: Header recebido: {auth_header}")
        if not auth_header:
            await websocket.close(code=1008) # Policy Violation
            return None
        try:
            # Resolve dependencies at runtime (websockets can't use Depends inside loop)
            security = get_security()
            message_service = get_message_service()

            # 3. Limpar o prefixo 'Bearer ' se existir
            # Diferente do Depends, aqui recebemos a string bruta: "Bearer <token>"
            token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else auth_header

            # 4. Validar o token (usando a string limpa)
            decoded = await security.verify_permission(token, required_roles=["admin", "user"])
            attendant_id = decoded.get("_id")
            
        except Exception as e:
            # Se o token for inválido ou não tiver permissão
            await websocket.send_json({"type": "error", "message": "Unauthorized"})
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
                    result = await message_service.get_messages_by_phone(raw_data.get("phone"))

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
            return None


_routes = MessagesRoutes()
router = _routes.router