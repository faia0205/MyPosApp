from typing import Tuple

class PriceCalculator:
    """
    価格計算ロジック
    ※ 割引計算は DiscountManager へ移行済み
    """

    def calculate_profit_metrics(self, current_total: int, total_sales_today: int,
                               current_expenses: int, avg_price_target: int) -> Tuple[int, bool, str]:
        """利益目標までの残りなどを計算"""
        
        estimated_profit = (total_sales_today + current_total) - current_expenses
        is_red = False
        msg = "黒字達成!"
        
        if estimated_profit < 0:
            is_red = True
            target = avg_price_target if avg_price_target > 0 else 500
            needed = (abs(estimated_profit) // target) + 1
            msg = f"あと {needed} 個"

        return estimated_profit, is_red, msg