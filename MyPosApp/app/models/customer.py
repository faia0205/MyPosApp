from dataclasses import dataclass
from typing import Optional, Dict, Any
import json

@dataclass
class Customer:
    """客層データモデル"""
    id: Optional[int]
    label: str
    attributes_json: str = "{}"
    color: str = "#ffffff"
    display_order: int = 0
    is_active: bool = True

    @property
    def attributes(self) -> dict:
        try:
            return json.loads(self.attributes_json)
        except Exception:
            return {}

    def set_attributes(self, data: dict):
        self.attributes_json = json.dumps(data, ensure_ascii=False)

    def to_dict(self) -> Dict[str, Any]:
        """JSON出力用辞書変換"""
        return {
            "id": self.id,
            "label": self.label,
            "attributes": self.attributes, # JSON文字列ではなく辞書を展開して返す
            "color": self.color,
            "display_order": self.display_order,
            "is_active": self.is_active
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Customer':
        """辞書からモデル生成"""
        c = Customer(
            id=data.get("id"),
            label=data["label"],
            attributes_json="{}",
            color=data.get("color", "#ffffff"),
            display_order=data.get("display_order", 0),
            is_active=data.get("is_active", True)
        )
        c.set_attributes(data.get("attributes", {}))
        return c