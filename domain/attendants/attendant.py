from dataclasses import dataclass
from typing import List, Optional
class Attendant:
    name: str
    login: str
    password: str
    sector: str
    costumers : Optional[List[str]]
    _id: Optional[str]