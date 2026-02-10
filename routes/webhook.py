from fastapi import APIRouter, Request, HTTPException
from core.environment import get_environment
from client.whatsapp.V24 import WhatsAppClient
from core.dependencies import get_clients
# ===== ENVIO DE MENSAGENS =====

class WebhookRouter:
    def __init__(self):
        self.env = get_environment()
        self.router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
        self._client = get_clients()["whatsapp"]

    def _register_routes(self):
        """Register all document routes."""
        self.router.add_api_route(
            "/send-text",
            self.get_by_id,
            methods=["POST"]
        )
        self.router.add_api_route(
            "/send-image",
            self.create_document,
            methods=["POST"]
        )
        self.router.add_api_route(
            "/send-document",
            self.create_document,
            methods=["POST"]
        )
        self.router.add_api_route(
            "/send-video",
            self.update_document,
            methods=["POST"]
        )
        self.router.add_api_route(
            "/webhook",
            self.delete_document,
            methods=["POST"]
        )
        self.router.add_api_route(
            "/webhook",
            self.delete_document,
            methods=["GET"]
        )

    async def send_text(self, to: str, text: str):
        try:
            return self._client.send_text(to=to, text=text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    async def send_image(self, to: str, image_url: str, caption: str = None):
        try:
            return self._client.send_image(to=to, image_url=image_url, caption=caption)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    async def send_video(self,to: str, video_url: str, caption: str = None):
        try:
            return self._client.send_video(to=to, video_url=video_url, caption=caption)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    async def send_document(self,to: str, document_url: str, caption: str = None, filename: str = None):
        try:
            return self._client.send_document(
                to=to,
                document_url=document_url,
                caption=caption,
                filename=filename
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    # ===== WEBHOOK =====
    async def verify_webhook(self,request: Request):
        return await self._client.verify_webhook(request)


    async def receive_webhook(self,request: Request):
        data = await request.json()
        messages = self._client.process_webhook(data)

        # Aqui você pode:
        # - salvar no banco
        # - mandar pra fila
        # - integrar com ERP
        print("Mensagens processadas:", messages)

        return {"status": "ok"}

# Instanciar e exportar router
_routes = WebhookRouter()
router = _routes.router