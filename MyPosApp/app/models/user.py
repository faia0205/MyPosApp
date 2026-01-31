from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class User:
    id: Optional[int]
    name: str
    user_code: str
    role: str
    is_active: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "user_code": self.user_code,
            "role": self.role,
            "is_active": self.is_active
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'User':
        return User(
            id=data.get("id"),
            name=data["name"],
            user_code=data["user_code"],
            role=data.get("role", "staff"),
            is_active=data.get("is_active", True)
        )