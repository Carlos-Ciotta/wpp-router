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
    message_shortcuts: Dict[str, str] = field(default_factory=dict)
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

    def is_bcrypt_hash(self, s: str) -> bool:
        return bool(re.match(r'^\$2[aby]\$\d{2}\$.{53}$', s))
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def to_dict(self):
        data = asdict(self)
        
        # Remove _id if None to allow MongoDB to generate it
        if data.get("_id") is None:
            if "_id" in data: del data["_id"]
        else:
            data["_id"] = self._id
        
        # Convert Enum to value
        if isinstance(self.permission, PermissionLevel):
            data["permission"] = self.permission.value
            
        return data
