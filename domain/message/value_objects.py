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
class MessageContext:
    """Informações de contexto (quando o usuário responde a uma mensagem)"""
    id: str  # O WAMID da mensagem que foi respondida
    from_number: Optional[str] = None # Quem enviou a mensagem original

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "from": self.from_number}

    @classmethod
    def from_webhook(cls, data: Dict[str, Any]) -> Optional['MessageContext']:
        if not data:
            return None
        return cls(
            id=data.get("id"),
            from_number=data.get("from")
        )
    
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
    type: str  
    reply_id: str
    title: str
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_webhook(cls, data: Dict[str, Any], itype: str) -> Optional['InteractiveReply']:
        if not data: return None
        
        # Mapeia list_reply e button_reply para nomes mais amigáveis
        simple_type = "list" if itype == "list_reply" else "button"
        
        return cls(
            type=simple_type,
            reply_id=data.get("id", ""),
            title=data.get("title", "") or data.get("text", ""), # buttons usam 'text' as vezes
            description=data.get("description")
        )