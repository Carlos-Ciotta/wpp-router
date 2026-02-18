"""Rotas para webhooks e envio de mensagens."""
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from client.whatsapp.V24 import WhatsAppClient
from core.dependencies import get_clients, get_chat_service, get_security

fastapi_security = HTTPBearer()

class WebhookRoutes():
    def __init__(self):
        self.router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])
        # Do not call async dependency factories at import time.
        # Route handlers receive required objects via FastAPI `Depends`.
        self._security = None
        self._client = None
        self._chat_service = None
        self._register_routes()

    async def get_whatsapp_client(self) -> WhatsAppClient:
        """Dependency para obter o client do WhatsApp."""
        clients = await get_clients()
        return clients["whatsapp"]


async def get_whatsapp_client() -> WhatsAppClient:
    """Module-level dependency to obtain the WhatsApp client."""
    clients = await get_clients()
    return clients["whatsapp"]

    def _register_routes(self):
        self.router.add_api_route("/templates", self.list_templates, methods=["GET"])
        self.router.add_api_route("/templates/sync", self.sync_templates, methods=["POST"])
        self.router.add_api_route("/webhook", self.verify_webhook, methods=["GET"])
        self.router.add_api_route("/webhook", self.receive_webhook, methods=["POST"])

    async def list_templates(self,
        token: HTTPAuthorizationCredentials = Depends(fastapi_security),
        security = Depends(get_security),
        chat_service = Depends(get_chat_service),
    ):
        """Lista templates do repositório local."""
        try:
            security.verify_permission(token.credentials, ["admin", "user"])
            return await chat_service.list_templates()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def sync_templates(self,
        token: HTTPAuthorizationCredentials = Depends(fastapi_security),
        security = Depends(get_security),
        chat_service = Depends(get_chat_service),
    ):
        """Força sincronização de templates do WhatsApp para o repositório local."""
        try:
            security.verify_permission(token.credentials, ["admin", "user"])
            templates = await chat_service.sync_templates_from_whatsapp()
            return {"count": len(templates), "message": "Templates sincronizados com sucesso."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def verify_webhook(self, request: Request, client: WhatsAppClient = Depends(get_whatsapp_client)):
        """Verificação do webhook (GET)"""
        return await client.verify_webhook(request)

    async def receive_webhook(
        self,
        request: Request,
        client: WhatsAppClient = Depends(get_whatsapp_client),
        chat_service = Depends(get_chat_service),
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


_routes = WebhookRoutes()
router = _routes.router