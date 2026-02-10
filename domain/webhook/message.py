"""
Domain Models para WhatsApp Cloud API v24.0 com MongoDB
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
from domain.webhook.value_objects import MediaInfo, InteractiveReply, MessageStatus
from domain.webhook.types import MessageType

@dataclass
class Message:
    """
    Entidade de domínio: Mensagem do WhatsApp
    Representa uma mensagem recebida via webhook
    """
    message_id: str
    from_number: str
    timestamp: int
    type: MessageType
    
    # Conteúdo
    text: Optional[str] = None
    media: Optional[MediaInfo] = None
    interactive: Optional[InteractiveReply] = None
    
    # Metadados
    profile_name: Optional[str] = None
    received_at: datetime = field(default_factory=datetime.utcnow)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    # Status
    status: Optional[MessageStatus] = None
    # MongoDB
    _id: Optional[str] = None
    
    def __post_init__(self):
        """Normaliza número para formato brasileiro"""
        # Remove + e espaços
        phone = str(self.from_number).lstrip("+").strip()
        
        # Normaliza número brasileiro: se tiver 12 dígitos, adiciona o 9
        if phone.startswith("55") and len(phone) == 12:
            phone = phone[:4] + "9" + phone[4:]
        
        self.from_number = phone

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário (para MongoDB)"""
        result = {
            "message_id": str(self.message_id),
            "from_number": str(self.from_number),
            "timestamp": str(self.timestamp),
            "type": str(self.type),
            "text": self.text,
            "profile_name": self.profile_name,
            "received_at": self.received_at,
            "raw_data": self.raw_data
        }
        
        if self.media:
            result["media"] = self.media.to_dict()
        
        if self.interactive:
            result["interactive"] = self.interactive.to_dict()

        if self._id:
            result["_id"] = self._id
        
        return result
    
    @classmethod
    def from_webhook(cls, data: Dict[str, Any], profile_name: Optional[str] = None) -> 'Message':
        """
        Cria Message a partir dos dados do webhook
        
        Args:
            data: Dados brutos do webhook
            profile_name: Nome do perfil do contato
        
        Returns:
            Instância de Message
        
        Example:
            message = Message.from_webhook({
                "id": "wamid.XXX",
                "from": "5511999999999",
                "timestamp": "1234567890",
                "type": "text",
                "text": {"body": "Olá!"}
            })
        """
        msg_id = data.get("id", "")
        from_number = data.get("from", "")
        timestamp = data.get("timestamp", "")
        msg_type = MessageType(data.get("type", "text"))
        
        # Extrai texto
        text = None
        if msg_type.value == "text":
            text = data.get("text", {}).get("body")
        
        # Extrai mídia
        media = None
        if msg_type.is_media:
            media_data = data.get(msg_type.value, {})
            media = MediaInfo.from_webhook(media_data)
        
        # Extrai interativo
        interactive = None
        if msg_type.is_interactive:
            interactive_data = data.get("interactive", {})
            interactive_type = interactive_data.get("type")
            
            if interactive_type == "button_reply":
                reply_data = interactive_data.get("button_reply", {})
                interactive = InteractiveReply.from_webhook(reply_data, "button_reply")
            elif interactive_type == "list_reply":
                reply_data = interactive_data.get("list_reply", {})
                interactive = InteractiveReply.from_webhook(reply_data, "list_reply")
        
        return cls(
            message_id=msg_id,
            from_number=from_number,
            timestamp=timestamp,
            type=msg_type,
            text=text,
            media=media,
            interactive=interactive,
            profile_name=profile_name,
            raw_data=data
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Reconstrói Message a partir de dicionário do MongoDB"""
        return cls(
            message_id=data["message_id"],
            from_number=data["from_number"],
            timestamp=data["timestamp"],
            type=MessageType(data["type"]),
            text=data.get("text"),
            media=MediaInfo(**data["media"]) if data.get("media") else None,
            interactive=InteractiveReply(**data["interactive"]) if data.get("interactive") else None,
            profile_name=data.get("profile_name"),
            received_at=data.get("received_at", datetime.utcnow()),
            raw_data=data.get("raw_data", {}),
            _id=data.get("_id")
        )