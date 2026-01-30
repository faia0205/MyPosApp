from typing import List, Dict, Tuple
from app.models.cart_item import CartItem

class PriceCalculator:
    """価格計算ロジック（オブジェクト対応版）"""

    def calculate_items_subtotal(self, items: List[CartItem]) -> int:
        return sum(item.price * item.qty for item in items)

    def calculate_profit_metrics(self, current_total: int, total_sales_today: int, 
                                 current_expenses: int, avg_price_target: int) -> Tuple[int, bool, str]:
        # このロジックは依存がないので変更なし
        estimated_profit = (total_sales_today + current_total) - current_expenses
        is_red = False
        msg = "黒字達成!"
        if estimated_profit < 0:
            is_red = True
            target = avg_price_target if avg_price_target > 0 else 500
            needed = (abs(estimated_profit) // target) + 1
            msg = f"あと {needed} 個"
        return estimated_profit, is_red, msg