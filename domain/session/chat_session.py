from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class SessionStatus(str, Enum):
    WAITING_MENU = "waiting_menu"
    ACTIVE = "active"
    CLOSED = "closed"

class ChatSession(BaseModel):
    phone_number: str
    status: SessionStatus = SessionStatus.WAITING_MENU
    attendant_id: Optional[str] = None
    category: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_interaction_at: datetime = Field(default_factory=datetime.now)
    _id: Optional[str] = None
