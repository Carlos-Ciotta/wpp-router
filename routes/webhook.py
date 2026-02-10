from fastapi import APIRouter, Request, HTTPException
from core.environment import get_environment
from client.whatsapp.V24 import WhatsAppClient

env = get_environment()
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

# Instância única do client
client = WhatsAppClient(
    phone_id=env.WHATSAPP_PHONE_ID,
    wa_token=env.WHATSAPP_TOKEN,
    base_url=f"https://graph.facebook.com/v24.0/{env.WHATSAPP_PHONE_ID}/messages",
    internal_token=env.WHATSAPP_INTERNAL_TOKEN
)

# ===== ENVIO DE MENSAGENS =====

@router.post("/send/text")
def send_text(to: str, text: str):
    try:
        return client.send_text(to=to, text=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/image")
def send_image(to: str, image_url: str, caption: str = None):
    try:
        return client.send_image(to=to, image_url=image_url, caption=caption)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/video")
def send_video(to: str, video_url: str, caption: str = None):
    try:
        return client.send_video(to=to, video_url=video_url, caption=caption)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/document")
def send_document(to: str, document_url: str, caption: str = None, filename: str = None):
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
async def verify_webhook(request: Request):
    return await client.verify_webhook(request)


@router.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    messages = client.process_webhook(data)

    # Aqui você pode:
    # - salvar no banco
    # - mandar pra fila
    # - integrar com ERP
    print("Mensagens processadas:", messages)

    return {"status": "ok"}

