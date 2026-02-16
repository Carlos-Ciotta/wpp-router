from fastapi import APIRouter, Depends, HTTPException, Body, WebSocket
from typing import Optional, List, Dict, Any
import json
from core.dependencies import get_chat_service
from services.chat_service import ChatService
from utils.auth import PermissionChecker # Importe seu ConnectionManager global
from core.websocket import manager
# Instâncias de permissão
admin_permission = PermissionChecker(allowed_permissions=["admin"])
user_permission = PermissionChecker(allowed_permissions=["user", "admin"])

router = APIRouter(prefix="/messages", tags=["Messages"])
@router.websocket("/ws")
async def chat_endpoint(
    websocket: WebSocket,
    auth_data: dict = Depends(user_permission)
):
    user_id = auth_data.get("_id")
    # Injetamos o serviço manualmente pois Depends não funciona dentro do while True
    chat_service = await get_chat_service() 
    
    await manager.connect(user_id, websocket)
    
    try:
        while True:
            # Recebe a mensagem do Front-end (JSON)
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            
            action = data.get("action") # ex: "send_text", "send_image"
            payload = data.get("payload", {})
            
            try:
                # --- DISPATCHER DE COMANDOS ---
                match action:
                    case "send_text":
                        result = await chat_service.send_text_message(
                        to=payload.get("to"), 
                        text=payload.get("text")
                        )
                        await manager.send_personal_message({"type": "success", "action": action}, user_id)

                    case "send_video":
                        result = await chat_service.send_video_message(
                        to=payload.get("to"),
                        video_url=payload.get("video_url"),
                        caption=payload.get("caption")
                        )
                        await manager.send_personal_message({"type": "success", "action": action}, user_id)
                    case "send_document":
                        result = await chat_service.send_document_message(
                        to=payload.get("to"),
                        document_url=payload.get("document_url"),
                        caption=payload.get("caption"),
                        filename=payload.get("filename")
                        )
                        await manager.send_personal_message({"type": "success", "action": action}, user_id)
                    
                    case "send_audio":
                        result = await chat_service.send_audio_message(
                        to=payload.get("to"),
                        audio_url=payload.get("audio_url"),
                        caption=payload.get("caption")
                        )
                        await manager.send_personal_message({"type": "success", "action": action}, user_id)
                    
                    case "send_image":
                        result = await chat_service.send_image_message(
                        to=payload.get("to"), 
                        image_url=payload.get("image_url"), 
                        caption=payload.get("caption")
                        )
                        await manager.send_personal_message({"type": "success", "action": action}, user_id)

                    case "send_interactive":
                        result = await chat_service.send_interactive_message(
                        to=payload.get("to"),
                        header=payload.get("header"),
                        body=payload.get("body"),
                        footer=payload.get("footer"),
                        buttons=payload.get("buttons")
                        )
                        await manager.send_personal_message({"type": "success", "action": action}, user_id)
                    
                    case "send_list":
                        result = await chat_service.send_list_message(
                        to=payload.get("to"),
                        header=payload.get("header"),
                        body=payload.get("body"),
                        footer=payload.get("footer"),
                        button_text=payload.get("button_text"),
                        sections=payload.get("sections")
                        )
                        await manager.send_personal_message({"type": "success", "action": action}, user_id)
                    
                    case "send_template":
                        result = await chat_service.send_template_message(
                        to=payload.get("to"),
                        template_name=payload.get("template_name"),
                        language_code=payload.get("language_code", "pt_BR"),
                        components=payload.get("components")
                        )
                        await manager.send_personal_message({"type": "success", "action": action}, user_id)

                    case "get_messages":
                        result = await chat_service.get_messages_by_phone(
                        phone=payload.get("phone"),
                        limit=payload.get("limit", 50),
                        skip=payload.get("skip", 0))
                        await manager.send_personal_message({
                            "type": "success",
                            "action": action,
                            "data": result
                        }, user_id)
            except Exception as e:
                await manager.send_personal_message({
                    "type": "error", 
                    "action": action, 
                    "message": str(e)
                }, user_id)

    except Exception:
        manager.disconnect(user_id)
'''
@router.post("/text")
async def send_text_message(
    to: str = Body(..., description="Número do destinatário"),
    text: str = Body(..., description="Conteúdo da mensagem"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Envia mensagem de texto simples.
    Requer janela de conversação de 24h aberta.
    """
    try:
        return await chat_service.send_text_message(to, text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/image")
async def send_image_message(
    to: str = Body(..., description="Número do destinatário"),
    image_url: str = Body(..., description="URL da imagem"),
    token: str = Depends(user_permission), # Both users and admins can send messages
    caption: Optional[str] = Body(None, description="Legenda da imagem"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Envia imagem por URL.
    Requer janela de conversação de 24h aberta.
    """
    try:
        return await chat_service.send_image_message(to, image_url, caption)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/video")
async def send_video_message(
    to: str = Body(..., description="Número do destinatário"),
    video_url: str = Body(..., description="URL do vídeo"),
    token: str = Depends(user_permission), # Both users and admins can send messages
    caption: Optional[str] = Body(None, description="Legenda do vídeo"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Envia vídeo por URL.
    Requer janela de conversação de 24h aberta.
    """
    try:
        return await chat_service.send_video_message(to, video_url, caption)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/document")
async def send_document_message(
    to: str = Body(..., description="Número do destinatário"),
    document_url: str = Body(..., description="URL do documento"),
    token: str = Depends(user_permission), # Both users and admins can send messages
    caption: Optional[str] = Body(None, description="Legenda do arquivo"),
    filename: Optional[str] = Body(None, description="Nome do arquivo"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Envia documento por URL.
    Requer janela de conversação de 24h aberta.
    """
    try:
        return await chat_service.send_document_message(to, document_url, caption, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/template")
async def send_template_message(
    to: str = Body(..., description="Número do destinatário"),
    template_name: str = Body(..., description="Nome do template aprovado"),
    token: str = Depends(user_permission), # Both users and admins can send messages
    language_code: str = Body("pt_BR", description="Código do idioma (ex: pt_BR)"),
    components: Optional[List[Dict[str, Any]]] = Body(None, description="Componentes variáveis do template"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Envia mensagem de Template (HSM).
    Pode ser usado para iniciar conversas fora da janela de 24h.
    """
    try:
        return await chat_service.send_template_message(to, template_name, language_code, components)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''