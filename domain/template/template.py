from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class TemplateComponent(BaseModel):
    type: str
    format: Optional[str] = None
    text: Optional[str] = None
    buttons: Optional[List[Dict[str, Any]]] = None
    example: Optional[Dict[str, Any]] = None

class Template(BaseModel):
    id: str
    name: str
    status: str
    category: str
    language: str
    components: List[Dict[str, Any]] = []
    
    class Config:
        from_attributes = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Template":
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            status=data.get("status"),
            category=data.get("category"),
            language=data.get("language"),
            components=data.get("components", [])
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.dict()
