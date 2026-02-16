from fastapi import APIRouter, WebSocket
import json
from core.dependencies import get_chat_service
from utils.auth import PermissionChecker # Importe seu ConnectionManager global
from core.websocket import manager
from handlers.ws.messages import HANDLERS

# Instâncias de permissão
admin_permission = PermissionChecker(allowed_permissions=["admin"])
user_permission = PermissionChecker(allowed_permissions=["user", "admin"])

router = APIRouter(prefix="/messages", tags=["Messages"])

@router.websocket("/ws")
async def chat_endpoint(
    websocket: WebSocket,
):
    """
    Retorna a última sessão de cada cliente atendido por um atendente específico.
    """
    await websocket.accept()
    # Injetamos o serviço manualmente pois Depends não funciona dentro do while True
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    payload = user_permission(token)
    attendant_id = payload.get("_id")
    chat_service = await get_chat_service()

    await manager.connect(attendant_id, websocket)
    
    while True:
        raw_data = await websocket.receive_text()
        data = json.loads(raw_data)

        action = data.get("action")
        payload = data.get("payload", {})

        handler = HANDLERS.get(action)

        if not handler:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Ação inválida: {action}"
            }, attendant_id)
            continue

        try:
            result = await handler(chat_service, payload)

            response = {
                "type": "success",
                "action": action
            }

            if action == "get_messages":
                response["data"] = result

            await manager.send_personal_message(response, attendant_id)

        except Exception as e:
            await manager.send_personal_message({
                "type": "error",
                "action": action,
                "message": str(e)
            }, attendant_id)

            manager.disconnect(attendant_id)
            break