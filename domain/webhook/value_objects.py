"""
Value Objects para WhatsApp Domain
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from enum import Enum


class MessageStatus(str, Enum):
    """Enum para status de mensagem"""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


@dataclass
class MediaInfo:
    """Informações de mídia"""
    id: Optional[str] = None
    link: Optional[str] = None
    caption: Optional[str] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    sha256: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    @classmethod
    def from_webhook(cls, data: Dict[str, Any]) -> Optional['MediaInfo']:
        """Cria MediaInfo a partir dos dados do webhook"""
        if not data:
            return None
        
        return cls(
            id=data.get("id"),
            link=data.get("link"),
            caption=data.get("caption"),
            filename=data.get("filename"),
            mime_type=data.get("mime_type"),
            sha256=data.get("sha256")
        )


@dataclass
class InteractiveReply:
    """Resposta interativa (botão ou lista)"""
    type: str  # button_reply ou list_reply
    reply_id: str
    title: str
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    @classmethod
    def from_webhook(cls, data: Dict[str, Any], reply_type: str) -> Optional['InteractiveReply']:
        """Cria InteractiveReply a partir dos dados do webhook"""
        if not data:
            return None
        
        if reply_type == "button_reply":
            return cls(
                type="button",
                reply_id=data.get("id", ""),
                title=data.get("title", "")
            )
        elif reply_type == "list_reply":
            return cls(
                type="list",
                reply_id=data.get("id", ""),
                title=data.get("title", ""),
                description=data.get("description")
            )
        
        return None



