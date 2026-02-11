"""Rotas para webhooks e envio de mensagens."""
from fastapi import APIRouter, Request, HTTPException, Depends, Body
from typing import Optional, Dict, Any, List

from client.whatsapp.V24 import WhatsAppClient
from core.dependencies import get_clients, get_chat_service
from services.chat_service import ChatService

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

async def get_whatsapp_client() -> WhatsAppClient:
    """Dependency para obter o client do WhatsApp."""
    clients = await get_clients()
    return clients["whatsapp"]

# ===== TEMPLATES =====

@router.get("/templates")
async def list_templates(client: WhatsAppClient = Depends(get_whatsapp_client)):
    """Lista templates aprovados pela Meta."""
    try:
        return client.get_templates(status="APPROVED")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send/template")
async def send_template(
    to: str = Body(..., description="Número do destinatário"),
    template_name: str = Body(..., description="Nome do template"),
    language_code: str = Body("pt_BR", description="Código do idioma"),
    components: Optional[List[Dict[str, Any]]] = Body(None, description="Componentes variáveis"),
    client: WhatsAppClient = Depends(get_whatsapp_client)
):
    """Envia mensagem de template (obrigatório para iniciar conversas fora da janela de 24h)."""
    try:
        return client.send_template(
            to=to, 
            template_name=template_name, 
            language_code=language_code, 
            components=components
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== ENVIO DE MENSAGENS =====

@router.post("/send/text")
async def send_text(
    to: str, 
    text: str, 
    client: WhatsAppClient = Depends(get_whatsapp_client),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Envia mensagem de texto livre.
    RESTRITIVO: Só funciona se houver uma janela de conversação aberta (24h).
    """
    if not await chat_service.can_send_free_message(to):
        raise HTTPException(
            status_code=400, 
            detail="Janela de 24h fechada. É necessário enviar um Template Message para iniciar/retomar a conversa."
        )

    try:
        return client.send_text(to=to, text=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/image")
async def send_image(
    to: str, 
    image_url: str, 
    caption: Optional[str] = None, 
    client: WhatsAppClient = Depends(get_whatsapp_client),
    chat_service: ChatService = Depends(get_chat_service)
):
    if not await chat_service.can_send_free_message(to):
        raise HTTPException(
            status_code=400, 
            detail="Janela de 24h fechada. É necessário enviar um Template Message para iniciar/retomar a conversa."
        )

    try:
        return client.send_image(to=to, image_url=image_url, caption=caption)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/video")
async def send_video(
    to: str, 
    video_url: str, 
    caption: Optional[str] = None, 
    client: WhatsAppClient = Depends(get_whatsapp_client),
    chat_service: ChatService = Depends(get_chat_service)
):
    if not await chat_service.can_send_free_message(to):
        raise HTTPException(
            status_code=400, 
            detail="Janela de 24h fechada. É necessário enviar um Template Message para iniciar/retomar a conversa."
        )

    try:
        return client.send_video(to=to, video_url=video_url, caption=caption)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/document")
async def send_document(
    to: str, 
    document_url: str, 
    caption: Optional[str] = None, 
    filename: Optional[str] = None, 
    client: WhatsAppClient = Depends(get_whatsapp_client),
    chat_service: ChatService = Depends(get_chat_service)
):
    if not await chat_service.can_send_free_message(to):
        raise HTTPException(
            status_code=400, 
            detail="Janela de 24h fechada. É necessário enviar um Template Message para iniciar/retomar a conversa."
        )

    try:
        return client.send_document(
            to=to,
            document_url=document_url,
            caption=caption,
            filename=filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== WEBHOOK =====

@router.get("/webhook")
async def verify_webhook(request: Request, client: WhatsAppClient = Depends(get_whatsapp_client)):
    """Verificação do webhook (GET)"""
    return await client.verify_webhook(request)


@router.post("/webhook")
async def receive_webhook(
    request: Request, 
    client: WhatsAppClient = Depends(get_whatsapp_client),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Recebimento de notificações (POST)"""
    try:
        data = await request.json()
        
        # O processamento e salvamento é feito pelo client/repo
        messages = await client.process_webhook(data)
        
        # Processamento da lógica de chat (Automação, Menus, Atribuição)
        for msg in messages:
            await chat_service.process_incoming_message(msg)
        
        # Log simplificado
        if messages:
             print(f"📥 Processado(s) {len(messages)} evento(s)")

        return {"status": "ok", "processed": len(messages)}
    except Exception as e:
        print(f"❌ Erro no webhook: {e}")
        # Retorna 200 sempre para evitar rereenvio infinito do WhatsApp
        return {"status": "error", "message": str(e)}