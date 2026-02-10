"""
WhatsApp Cloud API v24.0 - Cliente para envio de mensagens
Documentação: https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages
"""
import requests
from typing import List, Dict, Any, Optional
from core.environment import get_environment
from fastapi import APIRouter, HTTPException, Body, Request, Depends
from fastapi.responses import PlainTextResponse
from repositories.message import MessageRepository

env = get_environment()
class WhatsAppClient:
    """Cliente para enviar e receber mensagens via WhatsApp Cloud API v24.0"""
    
    def __init__(self, 
                 phone_id: str, 
                 wa_token: str , 
                 base_url: str ,
                 internal_token: str ,
                 repository:MessageRepository):
        self.phone_id = phone_id
        self._repo = repository
        self.wa_token = wa_token
        self._internal_token = internal_token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.wa_token}",
            "Content-Type": "application/json"
        }
    
    def _send_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Envia request para a API"""
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao enviar mensagem: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            raise
    
    def _sanitize_phone(self, phone: str) -> str:
        """Ajusta formatação do telefone (adiciona 9 para BR se necessário)"""
        # Se for BR (55) e tiver 12 dígitos (55 + 2 DDD + 8 NUM), adiciona o 9
        if phone and phone.startswith("55") and len(phone) == 12:
            return f"{phone[:4]}9{phone[4:]}"
        return phone

    def send_text(self, to: str, text: str, preview_url: bool = False) -> Dict[str, Any]:
        """
        Envia mensagem de texto
        
        Args:
            to: Número do destinatário (formato: 5511999999999)
            text: Texto da mensagem
            preview_url: Se True, mostra preview de links
        
        Returns:
            Resposta da API com message_id
        """
        to = self._sanitize_phone(to)
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text
            }
        }
        
        print(f"📤 Enviando texto para {to}: {text[:50]}...")
        return self._send_request(payload)
    
    def send_image(
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
        return self._send_request(payload)
    
    def send_video(
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
        return self._send_request(payload)
    
    def send_audio(
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
        return self._send_request(payload)
    
    def send_document(
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
        return self._send_request(payload)
    
    def send_buttons(
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
        return self._send_request(payload)
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
    
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Processa notificações recebidas do webhook
        
        Args:
            webhook_data: Dados JSON recebidos no POST do webhook
        
        Returns:
            Lista de mensagens processadas
        
        Example:
            messages = await client.process_webhook(request.json)
            for msg in messages:
                print(f"De: {msg['from']}, Tipo: {msg['type']}, Conteúdo: {msg['content']}")
        """
        messages = []
        
        try:
            if "entry" not in webhook_data:
                return messages
            
            for entry in webhook_data["entry"]:
                if "changes" not in entry:
                    continue
                
                for change in entry["changes"]:
                    if change.get("field") != "messages":
                        continue
                    
                    value = change.get("value", {})
                    
                    # Processa mensagens recebidas
                    if "messages" in value:
                        for message in value["messages"]:
                            parsed_msg = self._parse_message(message, value.get("contacts", []))
                            if parsed_msg:
                                messages.append(parsed_msg)
                    
                    # Processa status de mensagens enviadas
                    if "statuses" in value:
                        for status in value["statuses"]:
                            parsed_status = self._parse_status(status)
                            if parsed_status:
                                messages.append(parsed_status)
            
            if self._repo and messages:
                await self._repo.save_messages_bulk(messages)
            
            return messages
        
        except Exception as e:
            print(f"❌ Erro ao processar webhook: {e}")
            return messages
    
    def _parse_message(self, message: Dict[str, Any], contacts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Parser interno para mensagens recebidas
        
        Returns:
            Dict com: type, message_id, from, timestamp, from_name, content, context (se reply)
        """
        msg_type = message.get("type")
        message_id = message.get("id")
        from_number = message.get("from")
        timestamp = message.get("timestamp")
        
        # Pega nome do contato
        from_name = None
        for contact in contacts:
            if contact.get("wa_id") == from_number:
                from_name = contact.get("profile", {}).get("name")
                break
        
        # Contexto (resposta a outra mensagem)
        context = None
        if "context" in message:
            context = {
                "message_id": message["context"].get("id"),
                "from": message["context"].get("from")
            }
        
        parsed = {
            "event_type": "message",
            "type": msg_type,
            "message_id": message_id,
            "from": from_number,
            "from_name": from_name,
            "timestamp": timestamp,
            "context": context
        }
        
        # Processa conteúdo por tipo
        if msg_type == "text":
            parsed["content"] = message.get("text", {}).get("body", "")
        
        elif msg_type == "image":
            parsed["content"] = {
                "id": message.get("image", {}).get("id"),
                "mime_type": message.get("image", {}).get("mime_type"),
                "sha256": message.get("image", {}).get("sha256"),
                "caption": message.get("image", {}).get("caption")
            }
        
        elif msg_type == "video":
            parsed["content"] = {
                "id": message.get("video", {}).get("id"),
                "mime_type": message.get("video", {}).get("mime_type"),
                "sha256": message.get("video", {}).get("sha256"),
                "caption": message.get("video", {}).get("caption")
            }
        
        elif msg_type == "audio":
            parsed["content"] = {
                "id": message.get("audio", {}).get("id"),
                "mime_type": message.get("audio", {}).get("mime_type"),
                "sha256": message.get("audio", {}).get("sha256"),
                "voice": message.get("audio", {}).get("voice", False)
            }
        
        elif msg_type == "document":
            parsed["content"] = {
                "id": message.get("document", {}).get("id"),
                "mime_type": message.get("document", {}).get("mime_type"),
                "sha256": message.get("document", {}).get("sha256"),
                "filename": message.get("document", {}).get("filename"),
                "caption": message.get("document", {}).get("caption")
            }
        
        elif msg_type == "sticker":
            parsed["content"] = {
                "id": message.get("sticker", {}).get("id"),
                "mime_type": message.get("sticker", {}).get("mime_type"),
                "sha256": message.get("sticker", {}).get("sha256"),
                "animated": message.get("sticker", {}).get("animated", False)
            }
        
        elif msg_type == "location":
            loc = message.get("location", {})
            parsed["content"] = {
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "name": loc.get("name"),
                "address": loc.get("address")
            }
        
        elif msg_type == "contacts":
            parsed["content"] = message.get("contacts", [])
        
        elif msg_type == "button":
            # Resposta a botão
            parsed["content"] = {
                "payload": message.get("button", {}).get("payload"),
                "text": message.get("button", {}).get("text")
            }
        
        elif msg_type == "interactive":
            # Resposta a lista ou botão interativo
            interactive = message.get("interactive", {})
            interactive_type = interactive.get("type")
            
            if interactive_type == "button_reply":
                parsed["content"] = {
                    "id": interactive.get("button_reply", {}).get("id"),
                    "title": interactive.get("button_reply", {}).get("title")
                }
            elif interactive_type == "list_reply":
                parsed["content"] = {
                    "id": interactive.get("list_reply", {}).get("id"),
                    "title": interactive.get("list_reply", {}).get("title"),
                    "description": interactive.get("list_reply", {}).get("description")
                }
        
        elif msg_type == "reaction":
            parsed["content"] = {
                "message_id": message.get("reaction", {}).get("message_id"),
                "emoji": message.get("reaction", {}).get("emoji")
            }
        
        elif msg_type == "order":
             parsed["content"] = {
                "catalog_id": message.get("order", {}).get("catalog_id"),
                "product_items": message.get("order", {}).get("product_items", []),
                "text": message.get("order", {}).get("text")
             }
        
        elif msg_type == "system":
            parsed["content"] = {
                "body": message.get("system", {}).get("body"),
                "identity": message.get("system", {}).get("identity"),
                "new_wa_id": message.get("system", {}).get("new_wa_id"),
                "type": message.get("system", {}).get("type"),
                "customer": message.get("system", {}).get("customer")
            }
        
        elif msg_type == "unknown":
             parsed["content"] = message.get("errors", [])
        
        else:
            parsed["content"] = message.get(msg_type, {})
        
        # Additional metadata commonly found in messages
        if "referral" in message:
            parsed["referral"] = message["referral"]

        print(f"📩 Mensagem recebida - De: {from_number} ({from_name}), Tipo: {msg_type}")
        return parsed
    
    def _parse_status(self, status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parser interno para status de mensagens enviadas
        
        Returns:
            Dict com: event_type='status', message_id, recipient, status, timestamp
        """
        parsed = {
            "event_type": "status",
            "message_id": status.get("id"),
            "recipient": status.get("recipient_id"),
            "status": status.get("status"),  # sent, delivered, read, failed
            "timestamp": status.get("timestamp")
        }
        
        # Se houver erro
        if "errors" in status:
            parsed["errors"] = status["errors"]
        
        # Informações de preço (para mensagens cobradas)
        if "pricing" in status:
            parsed["pricing"] = status["pricing"]
        
        # Informações da conversa (origin, expiration, etc)
        if "conversation" in status:
            parsed["conversation"] = status["conversation"]
        
        print(f"📊 Status recebido - Mensagem: {parsed['message_id']}, Status: {parsed['status']}")
        return parsed
    
    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Marca uma mensagem como lida
        
        Args:
            message_id: ID da mensagem recebida
        
        Returns:
            Resposta da API
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        return self._send_request(payload)

    # ===== GESTÃO DE MÍDIA (UPLOAD/DOWNLOAD) =====

    def get_media_url(self, media_id: str) -> Optional[str]:
        """
        Recupera a URL de download de uma mídia recebida pelo ID.
        API: GET /v24.0/{media-id}
        """
        try:
            url = f"https://graph.facebook.com/v24.0/{media_id}"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("url")
        except Exception as e:
            print(f"❌ Erro ao obter URL da mídia {media_id}: {e}")
            return None

    def download_media(self, media_url: str) -> Optional[bytes]:
        """
        Baixa o binário da mídia usando a URL obtida.
        Requer header Authorization: Bearer {token}
        """
        try:
            response = requests.get(media_url, headers=self.headers, timeout=60)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"❌ Erro ao baixar mídia: {e}")
            return None

    def upload_media(self, file_path: str, mime_type: str) -> Optional[str]:
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
                
                response = requests.post(
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