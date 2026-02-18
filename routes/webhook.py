"""Rotas para webhooks e envio de mensagens."""
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from client.whatsapp.V24 import WhatsAppClient
from core.dependencies import get_clients, get_chat_service, get_security

fastapi_security = HTTPBearer()

class WebhookRoutes():
    def __init__(self):
        self.router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])
        self._security = get_security()
        self._client = get_clients()["whatsapp"]
        self._chat_service = get_chat_service()
        self._register_routes()

    def _register_routes(self):
        self.router.add_api_route("/templates", self.list_templates, methods=["GET"])
        self.router.add_api_route("/templates/sync", self.sync_templates, methods=["POST"])
        self.router.add_api_route("/webhook", self.verify_webhook, methods=["GET"])
        self.router.add_api_route("/webhook", self.receive_webhook, methods=["POST"])

    async def list_templates(self,
        token: HTTPAuthorizationCredentials = Depends(fastapi_security),
    ):
        """Lista templates do repositório local."""
        try:
            self._security.verify_permission(token.credentials, ["admin", "user"])
            return await self._chat_service.list_templates()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def sync_templates(self,
        token: HTTPAuthorizationCredentials = Depends(fastapi_security),
    ):
        """Força sincronização de templates do WhatsApp para o repositório local."""
        try:
            self._security.verify_permission(token.credentials, ["admin", "user"])
            templates = await self._chat_service.sync_templates_from_whatsapp()
            return {"count": len(templates), "message": "Templates sincronizados com sucesso."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def verify_webhook(self, request: Request,):
        """Verificação do webhook (GET)"""
        return await self._client.verify_webhook(request)

    async def receive_webhook(
        self,
        request: Request,
    ):
        """Recebimento de notificações (POST)"""
        try:
            data = await request.json()
            
            # O processamento e salvamento é feito pelo client/repo
            messages = await self._client.process_webhook(data)
            
            # Processamento da lógica de chat (Automação, Menus, Atribuição)
            for msg in messages:
                await self._chat_service.process_incoming_message(msg)
            
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