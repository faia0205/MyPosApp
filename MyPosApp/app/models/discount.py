from dataclasses import dataclass
from typing import Optional

@dataclass
class DiscountRule:
    """割引ルール定義 (DB: discount_rules)"""
    id: Optional[int]
    name: str
    discount_type: str      # 'fixed' (円) or 'percent' (%)
    discount_value: int
    apply_type: str         # 'cart', 'category', 'item', 'bundle'
    target_value: str       # 対象識別子 (JSON文字列 または カテゴリ名/商品名)
    is_auto: bool = False   # 自動適用するか
    is_active: bool = True

@dataclass
class AppliedDiscount:
    """計算結果として適用された割引"""
    rule_id: int
    name: str
    amount: int  # 割引額（負の値。例: -100）
    qty: int     # 適用セット数