"""
WhatsApp Cloud API v24.0 - Cliente para envio de mensagens
Documentação: https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages
"""
import httpx
from typing import List, Dict, Any, Optional
from core.environment import get_environment
from fastapi import APIRouter, HTTPException, Body, Request, Depends
from fastapi.responses import PlainTextResponse
from repositories.message import MessageRepository
from domain.message.message import Message
env = get_environment()
class WhatsAppClient:
    """Cliente para enviar e receber mensagens via WhatsApp Cloud API v24.0"""
    
    def __init__(self, 
                 phone_id: str, 
                 business_account_id: str,
                 wa_token: str , 
                 base_url: str ,
                 internal_token: str ,
                 repository:MessageRepository,):
        self.phone_id = phone_id
        self.business_account_id = business_account_id
        self._repo = repository
        self.wa_token = wa_token
        self._internal_token = internal_token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.wa_token}",
            "Content-Type": "application/json"
        }
    

    async def _send_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Envia request para a API"""
        try:
            # Note: requests is synchronous and will block the event loop.
            # Ideally use httpx.AsyncClient or run_in_executor.
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/{self.phone_id}/messages",
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
            response.raise_for_status()
            res_data = response.json()
        
            # 1. Extrai o ID da mensagem gerado pela Meta
            # A estrutura da resposta é: {"messages": [{"id": "wamid.ID..."}]}
            wa_message_id = res_data.get("messages", [{}])[0].get("id")

            # 2. Prepara os dados para o banco
            save_payload = payload.copy()
            save_payload.pop("messaging_product", None)
            save_payload.pop("recipient_type", None)
            save_payload['direction'] = 'outgoing'
            save_payload['message_id'] = wa_message_id  # <--- AGORA TEM ID!

            # 3. Salva no banco com o ID correto
            if wa_message_id:
                await self._repo.save_messages_bulk([save_payload])
            return response.json()
        except httpx.exceptions.RequestException as e:
            print(f"❌ Erro na API WhatsApp: {e.response.text if e.response else e}")
            raise
    
    def _sanitize_phone(self, phone: str) -> str:
        """Ajusta formatação do telefone (adiciona 9 para BR se necessário)"""
        # Se for BR (55) e tiver 12 dígitos (55 + 2 DDD + 8 NUM), adiciona o 9
        if not phone:
            return phone
        if phone.startswith("55") and len(phone) == 12:
            # older format without the ninth digit
            return f"{phone[:4]}9{phone[4:]}"
        return phone

    async def get_templates(self, status: str = "APPROVED") -> List[Dict[str, Any]]:
        """
        Busca templates aprovados pela Meta
        
        Args:
            status: Status dos templates a buscar (default: APPROVED)
        """
        try:
            url = f"{self.base_url}/{self.business_account_id}/message_templates"
            params = {
                "status": status,
                "limit": 100 # Paginação pode ser necessária se houver muitos
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except httpx.exceptions.RequestException as e:
            print(f"❌ Erro ao buscar templates: {e.response.text if e.response else e}")
            raise

    async def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "pt_BR",
        components: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Envia mensagem de template
        
        Args:
            to: Número do destinatário
            template_name: Nome do template
            language_code: Código do idioma (default: pt_BR)
            components: Componentes variáveis do template (header, body, etc)
        """
        to = self._sanitize_phone(to)
        
        template_payload = {
            "name": template_name,
            "language": {
                "code": language_code
            }
        }
        
        if components:
            template_payload["components"] = components
            
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": template_payload
        }
        
        print(f"📤 Enviando template '{template_name}' para {to}")
        return await self._send_request(payload)

    async def send_text(self, to: str, text: str, preview_url: bool = False) -> Dict[str, Any]:
        # A normalização agora pode ser feita via Message ou mantida aqui por segurança
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": preview_url, "body": text}
        }
        return await self._send_request(payload)
    
    async def send_image(
        self, 
        to: str, 
        image_url: str = None, 
        image_id: str = None,
        caption: str = None
    ) -> Dict[str, Any]:
        """
        Envia imagem
        
        Args:
            to: Número do destinatário
            image_url: URL da imagem (HTTP/HTTPS)
            image_id: ID da mídia já enviada para WhatsApp
            caption: Legenda da imagem (opcional)
        
        Note: Use image_url OU image_id, não ambos
        """
        to = self._sanitize_phone(to)
        image_data = {}
        
        if image_id:
            image_data["id"] = image_id
        elif image_url:
            image_data["link"] = image_url
        else:
            raise ValueError("Forneça image_url ou image_id")
        
        if caption:
            image_data["caption"] = caption
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": image_data
        }
        
        print(f"📤 Enviando imagem para {to}")
        return await self._send_request(payload)
    
    async def send_video(
        self,
        to: str,
        video_url: str = None,
        video_id: str = None,
        caption: str = None
    ) -> Dict[str, Any]:
        """
        Envia vídeo
        
        Args:
            to: Número do destinatário
            video_url: URL do vídeo (HTTP/HTTPS)
            video_id: ID da mídia já enviada
            caption: Legenda (opcional)
        """
        to = self._sanitize_phone(to)
        video_data = {}
        
        if video_id:
            video_data["id"] = video_id
        elif video_url:
            video_data["link"] = video_url
        else:
            raise ValueError("Forneça video_url ou video_id")
        
        if caption:
            video_data["caption"] = caption
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "video",
            "video": video_data
        }
        
        print(f"📤 Enviando vídeo para {to}")
        return await self._send_request(payload)
    
    async def send_audio(
        self,
        to: str,
        audio_url: str = None,
        audio_id: str = None
    ) -> Dict[str, Any]:
        """
        Envia áudio
        
        Args:
            to: Número do destinatário
            audio_url: URL do áudio
            audio_id: ID da mídia já enviada
        """
        to = self._sanitize_phone(to)
        audio_data = {}
        
        if audio_id:
            audio_data["id"] = audio_id
        elif audio_url:
            audio_data["link"] = audio_url
        else:
            raise ValueError("Forneça audio_url ou audio_id")
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "audio",
            "audio": audio_data
        }
        
        print(f"📤 Enviando áudio para {to}")
        return await self._send_request(payload)
    
    async def send_document(
        self,
        to: str,
        document_url: str = None,
        document_id: str = None,
        caption: str = None,
        filename: str = None
    ) -> Dict[str, Any]:
        """
        Envia documento
        
        Args:
            to: Número do destinatário
            document_url: URL do documento
            document_id: ID da mídia já enviada
            caption: Legenda (opcional)
            filename: Nome do arquivo (opcional)
        """
        to = self._sanitize_phone(to)
        document_data = {}
        
        if document_id:
            document_data["id"] = document_id
        elif document_url:
            document_data["link"] = document_url
        else:
            raise ValueError("Forneça document_url ou document_id")
        
        if caption:
            document_data["caption"] = caption
        if filename:
            document_data["filename"] = filename
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "document",
            "document": document_data
        }
        
        print(f"📤 Enviando documento para {to}")
        return await self._send_request(payload)
    
    async def send_buttons(
        self,
        to: str,
        body_text: str,
        buttons: List[Dict[str, str]],
        header_text: str = None,
        footer_text: str = None
    ) -> Dict[str, Any]:
        """
        Envia mensagem com botões (máximo 3 botões)
        
        Args:
            to: Número do destinatário
            body_text: Texto principal da mensagem
            buttons: Lista de botões [{"id": "btn1", "title": "Opção 1"}, ...]
            header_text: Cabeçalho (opcional)
            footer_text: Rodapé (opcional)
        
        Example:
            buttons = [
                {"id": "btn_sim", "title": "Sim"},
                {"id": "btn_nao", "title": "Não"}
            ]
        """
        to = self._sanitize_phone(to)
        
        if len(buttons) > 3:
            raise ValueError("Máximo de 3 botões permitidos")
        
        # Constrói os botões no formato da API
        action_buttons = []
        for btn in buttons:
            action_buttons.append({
                "type": "reply",
                "reply": {
                    "id": btn["id"],
                    "title": btn["title"][:20]  # Máximo 20 caracteres
                }
            })
        
        interactive_data = {
            "type": "button",
            "body": {
                "text": body_text
            },
            "action": {
                "buttons": action_buttons
            }
        }
        
        if header_text:
            interactive_data["header"] = {
                "type": "text",
                "text": header_text
            }
        
        if footer_text:
            interactive_data["footer"] = {
                "text": footer_text
            }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive_data
        }
        
        print(f"📤 Enviando botões para {to}")
        return await self._send_request(payload)
 # ===== RECEBIMENTO DE MENSAGENS =====
    
    async def verify_webhook(self, request:Request):

        """Webhook verification handshake.

        Must echo back hub.challenge when hub.verify_token matches configured token.
        """
        mode = request.query_params.get("hub.mode")
        challenge = request.query_params.get("hub.challenge")
        token = request.query_params.get("hub.verify_token")

        if mode == "subscribe" and token == self._internal_token and challenge:
            return PlainTextResponse(content=challenge, status_code=200)
        raise HTTPException(status_code=403, detail="Verification failed")
    
    
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> List[Message]:
        """
        Usa o Domain Model para processar o JSON complexo.
        """
        try:
            # DELEGAÇÃO: O modelo de domínio faz o parse de tudo (Mensagens e Status)
            events = Message.parse_webhook(webhook_data)
            
            if not events:
                return []

            # 1. Filtra as mensagens novas (exclui o tipo status_update)
            to_save = [e.to_dict() for e in events if e.type != "status_update"]

            # 2. Filtra os updates de status
            to_update = [e.to_dict() for e in events if e.type == "status_update"]

            # 3. Executa as operações em lote (Bulk)
            if to_save:
                await self._repo.save_messages_bulk(to_save)

            if to_update:
                # Aqui delegamos a lista inteira para o repositório tratar via Bulk Write do MongoDB
                await self._repo.update_message_status_bulk(to_update)
            
            return events
        
        except Exception as e:
            print(f"❌ Erro ao processar webhook no Client: {e}")
            return []

    # --- GESTÃO DE MÍDIA ---

    async def get_media_url(self, media_id: str) -> Optional[str]:
        """Recupera URL de download"""
        try:
            url = f"https://graph.facebook.com/v24.0/{media_id}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=30)
            return response.json().get("url")
        except Exception:
            return None

    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """Informa ao WhatsApp que a mensagem foi lida"""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        return await self._send_request(payload)

    async def download_media(self, media_url: str) -> Optional[bytes]:
        """
        Baixa o binário da mídia usando a URL obtida.
        Requer header Authorization: Bearer {token}
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(media_url, headers=self.headers, timeout=60)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"❌ Erro ao baixar mídia: {e}")
            return None

    async def upload_media(self, file_path: str, mime_type: str) -> Optional[str]:
        """
        Faz upload de arquivo local para WhatsApp -> Retorna ID.
        API: POST /v24.0/{phone_id}/media
        """
        url = f"https://graph.facebook.com/v24.0/{self.phone_id}/media"
        
        try:
            with open(file_path, "rb") as f:
                # 'file' é o campo obrigatório para o binário
                files = {"file": (file_path, f, mime_type)}
                data = {"messaging_product": "whatsapp"}
                
                # Requests gerencia multipart boundary automaticamente se não setarmos Content-Type manual
                # Mas precisamos do Authorization. Self.headers tem 'Content-Type': 'application/json', então criamos um novo header
                headers_upload = {"Authorization": f"Bearer {self.wa_token}"}
                
                response = httpx.post(
                    url, 
                    headers=headers_upload, 
                    files=files, 
                    data=data, 
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                print(f"✅ Mídia enviada! ID: {result.get('id')}")
                return result.get('id')
        except Exception as e:
            print(f"❌ Erro upload média: {e}")
            return None