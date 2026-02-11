from typing import Optional
from datetime import datetime
from enum import Enum

class SessionStatus(str, Enum):
    WAITING_MENU = "waiting_menu"
    ACTIVE = "active"
    CLOSED = "closed"

class ChatSession():
    phone_number: str
    status: SessionStatus = SessionStatus.WAITING_MENU
    created_at: datetime 
    last_interaction_at: datetime 
    attendant_id: Optional[str] = None
    category: Optional[str] = None
    _id: Optional[str] = None
