from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum

@dataclass
class Message:
    # Identificadores
    message_id: str
    from_number: str
    timestamp: int
    type: str # 'text', 'status', 'image', etc.
    
    # Metadados do Canal
    display_phone_number: Optional[str] = None
    phone_number_id: Optional[str] = None
    
    # Conteúdo (Mensagens)
    text: Optional[str] = None
    profile_name: Optional[str] = None
    context: Optional[dict] = None
    
    # Status e Precificação (Eventos de Status)
    status: Optional[str] = None # sent, delivered, read, failed
    conversation_id: Optional[str] = None
    pricing_category: Optional[str] = None # marketing, utility, etc.
    is_billable: bool = False
    
    # Sistema
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_data: Dict[str, Any] = field(default_factory=dict)
    _id: Optional[Any] = None

    def __post_init__(self):
        """Normaliza o telefone para o padrão 55 + DDD + 9 + Número"""
        if self.from_number:
            phone = "".join(filter(str.isdigit, str(self.from_number)))
            if phone.startswith("55") and len(phone) == 12:
                phone = f"{phone[:4]}9{phone[4:]}"
            self.from_number = phone

    @classmethod
    def parse_webhook(cls, webhook_data: Dict[str, Any]) -> List['Message']:
        """Analisa o JSON completo e retorna uma lista de objetos Message/Status"""
        results = []
        entries = webhook_data.get("entry", [])
        
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                metadata = value.get("metadata", {})
                
                # Extração de Metadados do WhatsApp
                phone_id = metadata.get("phone_number_id")
                display_phone = metadata.get("display_phone_number")

                # 1. PROCESSAR MENSAGENS RECEBIDAS
                if "messages" in value:
                    contacts = value.get("contacts", [])
                    contact_names = {c.get("wa_id"): c.get("profile", {}).get("name") for c in contacts}
                    
                    for msg in value["messages"]:
                        results.append(cls(
                            message_id=msg.get("id"),
                            from_number=msg.get("from"),
                            timestamp=int(msg.get("timestamp")),
                            type=msg.get("type"),
                            text=msg.get("text", {}).get("body") if msg.get("type") == "text" else None,
                            profile_name=contact_names.get(msg.get("from")),
                            context=msg.get("context"),
                            phone_number_id=phone_id,
                            display_phone_number=display_phone,
                            raw_data=msg
                        ))

                # 2. PROCESSAR STATUS DE MENSAGENS ENVIADAS
                if "statuses" in value:
                    for st in value["statuses"]:
                        pricing = st.get("pricing", {})
                        conv = st.get("conversation", {})
                        
                        results.append(cls(
                            message_id=st.get("id"),
                            from_number=st.get("recipient_id"), # Quem recebe o status
                            timestamp=int(st.get("timestamp")),
                            type="status_update",
                            status=st.get("status"),
                            conversation_id=conv.get("id"),
                            pricing_category=pricing.get("category"),
                            is_billable=pricing.get("billable", False),
                            phone_number_id=phone_id,
                            display_phone_number=display_phone,
                            raw_data=st
                        ))
        return results

    def to_dict(self) -> Dict[str, Any]:
        """Prepara os dados para o MongoDB limpando campos vazios"""
        data = asdict(self)
        if self._id: data["_id"] = self._id
        return {k: v for k, v in data.items() if v is not None}