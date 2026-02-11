from typing import List, Optional, Dict
from dataclasses import dataclass, field

@dataclass
class WorkInterval:
    start: str  # Format "HH:MM"
    end: str    # Format "HH:MM"

@dataclass
class Attendant:
    name: str = None
    login: str = None
    password: str = None
    sector: List[str] = field(default_factory=list)
    clients: List[str] = field(default_factory=list)
    welcome_message: Optional[str] = None
    # Key: Day of week (0=Monday, 6=Sunday), Value: List of intervals
    working_hours: Optional[Dict[str, List[WorkInterval]]] = None
    _id: Optional[str] = None

    def to_dict(self):
        from dataclasses import asdict
        return {k: v for k, v in asdict(self).items() if v is not None and k != "_id"}
        pass
