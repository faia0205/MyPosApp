from dataclasses import dataclass
from typing import Optional

@dataclass
class CartItem:
    """カート内の1商品を表現するデータクラス"""
    id: Optional[int]  # 手入力商品はNone
    name: str
    price: int
    qty: int = 1
    category: str = "その他"
    is_manual: bool = False
    note: str = ""

    @property
    def subtotal(self) -> int:
        return self.price * self.qty