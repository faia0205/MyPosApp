from dataclasses import dataclass

@dataclass
class Product:
    """商品データモデル"""
    id: int
    name: str
    price: int
    category: str
    color: str
    note: str = ""
    display_order: int = 0
    is_active: bool = True

    @property
    def display_price(self) -> str:
        """表示用の価格文字列（例: ¥500）"""
        return f"¥{self.price:,}"
    
    @property
    def is_discount(self) -> bool:
        """割引商品かどうか"""
        return self.price < 0