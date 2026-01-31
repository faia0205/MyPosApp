from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class Product:
    """商品データモデル"""
    id: Optional[int]
    name: str
    price: int
    category: str
    color: str
    note: str = ""
    display_order: int = 0
    is_active: bool = True

    @property
    def display_price(self) -> str:
        return f"¥{self.price:,}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "category": self.category,
            "color": self.color,
            "note": self.note,
            "display_order": self.display_order,
            "is_active": self.is_active
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Product':
        return Product(
            id=data.get("id"),
            name=data["name"],
            price=data["price"],
            category=data["category"],
            color=data.get("color", "#ffffff"),
            note=data.get("note", ""),
            display_order=data.get("display_order", 0),
            is_active=data.get("is_active", True)
        )
    
    @property
    def is_discount(self) -> bool:
        """割引商品かどうか"""
        return self.price < 0