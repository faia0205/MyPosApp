from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class PaymentMethod:
    id: int
    name: str
    is_cash: bool
    is_active: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "is_cash": self.is_cash,
            "is_active": self.is_active
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PaymentMethod':
        return PaymentMethod(
            id=data.get("id", 0),
            name=data["name"],
            is_cash=data.get("is_cash", False),
            is_active=data.get("is_active", True)
        )