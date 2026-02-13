from typing import List, Optional, Dict
from dataclasses import dataclass, field, asdict
import bcrypt
import re
from enum import Enum

class PermissionLevel(Enum):
    USER = "user"
    ADMIN = "admin"

@dataclass
class WorkInterval:
    start: str  # Format "HH:MM"
    end: str    # Format "HH:MM"

@dataclass
class Attendant:
    name: str = None
    login: str = None
    password: str = None
    permission: PermissionLevel = PermissionLevel.USER
    sector: List[str] = field(default_factory=list)
    clients: List[str] = field(default_factory=list)
    welcome_message: Optional[str] = None
    # Key: Day of week (0=Monday, 6=Sunday), Value: List of intervals
    working_hours: Optional[Dict[str, List[WorkInterval]]] = None
    _id: Optional[str] = None

    def __post_init__(self):
        # Ensure password is hashed
        if self.password and not self.is_bcrypt_hash(self.password):
            self.password = self.hash_password(self.password)

    # Password helpers
    def password_matches(self, password: str) -> bool:
        """Verify if the provided password matches the stored hashed password."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

    def is_bcrypt_hash(s: str) -> bool:
        return bool(re.match(r'^\$2[aby]\$\d{2}\$.{53}$', s))

    def hash_password(self) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(self.password.encode('utf-8'), salt)
        object.__setattr__(self, "password",hashed.decode('utf-8'))
    
    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None and k != "_id" or "password"}
