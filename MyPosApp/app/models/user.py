from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str
    user_code: str
    role: str
    is_active: bool