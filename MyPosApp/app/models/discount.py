from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class DiscountRule:
    """割引ルール定義 (DB: discount_rules)"""
    id: Optional[int]
    name: str
    discount_type: str # 'fixed' (円) or 'percent' (%)
    discount_value: int
    apply_type: str # 'cart', 'category', 'item', 'bundle'
    target_value: str # 対象識別子 (JSON文字列 または カテゴリ名/商品名)
    is_auto: bool = False # 自動適用するか
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "discount_type": self.discount_type,
            "discount_value": self.discount_value,
            "apply_type": self.apply_type,
            "target_value": self.target_value,
            "is_auto": self.is_auto,
            "is_active": self.is_active
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'DiscountRule':
        return DiscountRule(
            id=data.get("id"),
            name=data["name"],
            discount_type=data.get("discount_type", "fixed"),
            discount_value=data.get("discount_value", 0),
            apply_type=data.get("apply_type", "cart"),
            target_value=data.get("target_value", ""),
            is_auto=data.get("is_auto", False),
            is_active=data.get("is_active", True)
        )

@dataclass
class AppliedDiscount:
    """計算結果として適用された割引"""
    rule_id: int
    name: str
    amount: int # 割引額（負の値。例: -100）
    qty: int # 適用セット数