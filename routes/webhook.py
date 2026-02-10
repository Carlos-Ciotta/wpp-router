"""Rotas para webhooks e envio de mensagens."""
from fastapi import APIRouter, Request, HTTPException, Depends
from typing import Optional, Dict, Any

from client.whatsapp.V24 import WhatsAppClient
from core.dependencies import get_clients

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

async def get_whatsapp_client() -> WhatsAppClient:
    """Dependency para obter o client do WhatsApp."""
    clients = await get_clients()
    return clients["whatsapp"]

# ===== ENVIO DE MENSAGENS =====

@router.post("/send/text")
async def send_text(to: str, text: str, client: WhatsAppClient = Depends(get_whatsapp_client)):
    try:
        return client.send_text(to=to, text=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/image")
async def send_image(to: str, image_url: str, caption: Optional[str] = None, client: WhatsAppClient = Depends(get_whatsapp_client)):
    try:
        return client.send_image(to=to, image_url=image_url, caption=caption)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/video")
async def send_video(to: str, video_url: str, caption: Optional[str] = None, client: WhatsAppClient = Depends(get_whatsapp_client)):
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
    client: WhatsAppClient = Depends(get_whatsapp_client)
):
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
async def receive_webhook(request: Request, client: WhatsAppClient = Depends(get_whatsapp_client)):
    """Recebimento de notificações (POST)"""
    try:
        data = await request.json()
        
        # O processamento e salvamento é feito pelo client/repo
        messages = await client.process_webhook(data)
        
        # Log simplificado
        if messages:
             print(f"📥 Processado(s) {len(messages)} evento(s)")

        return {"status": "ok", "processed": len(messages)}
    except Exception as e:
        print(f"❌ Erro no webhook: {e}")
        # Retorna 200 sempre para evitar rereenvio infinito do WhatsApp
        return {"status": "error", "message": str(e)}