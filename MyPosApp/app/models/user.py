from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: Optional[int]
    name: str
    user_code: str
    role: str
    is_active: bool