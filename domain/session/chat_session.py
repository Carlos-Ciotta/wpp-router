from typing import Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

class SessionStatus(str, Enum):
    WAITING_MENU = "waiting_menu"
    ACTIVE = "active"
    CLOSED = "closed"

@dataclass
class ChatSession():
    phone_number: str
    created_at: int 
    last_interaction_at: int 
    status: str = SessionStatus.WAITING_MENU.value
    last_client_interaction_at: Optional[int]=None
    attendant_id: Optional[str] = None
    category: Optional[str] = None
    _id: Optional[str] = None

    def to_dict(self):
        return {
            "phone_number": self.phone_number,
            "status": self.status,
            "created_at": self.created_at,
            "last_interaction_at": self.last_interaction_at,
            "last_client_interaction_at": self.last_client_interaction_at,
            "attendant_id": self.attendant_id,
            "category": self.category,
        }