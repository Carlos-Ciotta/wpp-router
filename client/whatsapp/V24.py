"""
WhatsApp Cloud API v24.0 - Cliente para envio de mensagens
Documentação: https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages
"""
import requests
import json
from typing import List, Dict, Any, Optional
from config import WHATSAPP_API_URL, WHATSAPP_TOKEN, WHATSAPP_PHONE_ID


class WhatsAppClient:
    """Cliente para enviar mensagens via WhatsApp Cloud API v24.0"""
    
    def __init__(self, phone_id: str = None, token: str = None):
        self.phone_id = phone_id or WHATSAPP_PHONE_ID
        self.token = token or WHATSAPP_TOKEN
        self.base_url = f"{WHATSAPP_API_URL}/{self.phone_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
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
    
    def send_list(
        self,
        to: str,
        body_text: str,
        button_text: str,
        sections: List[Dict[str, Any]],
        header_text: str = None,
        footer_text: str = None
    ) -> Dict[str, Any]:
        """
        Envia mensagem com lista de opções
        
        Args:
            to: Número do destinatário
            body_text: Texto principal
            button_text: Texto do botão (ex: "Ver opções")
            sections: Lista de seções com opções
            header_text: Cabeçalho (opcional)
            footer_text: Rodapé (opcional)
        
        Example:
            sections = [{
                "title": "Produtos",
                "rows": [
                    {"id": "prod1", "title": "Produto 1", "description": "Descrição"},
                    {"id": "prod2", "title": "Produto 2"}
                ]
            }]
        """
        interactive_data = {
            "type": "list",
            "body": {
                "text": body_text
            },
            "action": {
                "button": button_text,
                "sections": sections
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
        
        print(f"📤 Enviando lista para {to}")
        return self._send_request(payload)
    
    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """Marca mensagem como lida"""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        return self._send_request(payload)
    
    def get_media_url(self, media_id: str) -> str:
        """
        Obtém URL de download de uma mídia
        
        Args:
            media_id: ID da mídia recebida no webhook
        
        Returns:
            URL temporária para download
        """
        url = f"{WHATSAPP_API_URL}/{media_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("url")
        except Exception as e:
            print(f"❌ Erro ao obter URL da mídia: {e}")
            raise
    
    def download_media(self, media_url: str, save_path: str) -> bool:
        """
        Faz download de uma mídia
        
        Args:
            media_url: URL obtida via get_media_url()
            save_path: Caminho para salvar o arquivo
        
        Returns:
            True se sucesso, False se erro
        """
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = requests.get(media_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Mídia salva em: {save_path}")
            return True
        except Exception as e:
            print(f"❌ Erro ao baixar mídia: {e}")
            return False


# Instância global para facilitar importação
whatsapp_client = WhatsAppClient()
