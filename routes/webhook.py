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
async def list_templates(chat_service: ChatService = Depends(get_chat_service)):
    """Lista templates do repositório local."""
    try:
        return await chat_service.list_templates()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/templates/sync")
async def sync_templates(chat_service: ChatService = Depends(get_chat_service)):
    """Força sincronização de templates do WhatsApp para o repositório local."""
    try:
        templates = await chat_service.sync_templates_from_whatsapp()
        return {"count": len(templates), "message": "Templates sincronizados com sucesso."}
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