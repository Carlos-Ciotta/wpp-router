from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional, List, Dict, Any
from core.dependencies import get_chat_service
from services.chat_service import ChatService

router = APIRouter(prefix="/messages", tags=["Messages"])

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
