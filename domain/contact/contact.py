from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class Contact(BaseModel):
    phone: str = Field(alias="_id") # Usando telefone como ID único
    name: Optional[str] = None
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    last_message_at: Optional[float] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.timestamp()
        }

    def to_dict(self):
        return self.dict(by_alias=True)
