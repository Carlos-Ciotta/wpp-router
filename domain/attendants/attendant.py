from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class WorkInterval(BaseModel):
    start: str  # Format "HH:MM"
    end: str    # Format "HH:MM"

class Attendant(BaseModel):
    name: str
    login: str
    password: str
    sector: str
    clients: List[str] = Field(default_factory=list)
    welcome_message: Optional[str] = None
    # Key: Day of week (0=Monday, 6=Sunday), Value: List of intervals
    working_hours: Optional[Dict[str, List[WorkInterval]]] = None
    _id: Optional[str] = None