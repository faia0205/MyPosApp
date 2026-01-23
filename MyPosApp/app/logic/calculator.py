from typing import List, Dict, Tuple
from app.models.cart_item import CartItem

class PriceCalculator:
    """価格計算ロジック（オブジェクト対応版）"""

    def calculate_items_subtotal(self, items: List[CartItem]) -> int:
        return sum(item.price * item.qty for item in items)

    def process_discounts(self, items: List[CartItem], rules: List[Dict]) -> List[Dict]:
        """
        ※このメソッドはDiscountManagerにロジックが移行していますが、
          簡易計算用に残す場合の互換性を維持します。
        """
        applied_discounts = []
        for rule in rules:
            target_count = 0
            for item in items:
                # item.id アクセスに変更
                if item.id is not None and item.id in rule.get('target_ids', []):
                    target_count += item.qty
            
            req = rule.get('req', 9999)
            apply_times = target_count // req
            
            if apply_times > 0:
                applied_discounts.append({
                    'name': rule['name'],
                    'amount': rule.get('amt', 0),
                    'qty': apply_times
                })
        return applied_discounts

    def calculate_grand_total(self, items: List[CartItem], discounts: List[Dict]) -> int:
        subtotal = self.calculate_items_subtotal(items)
        discount_total = sum(d['amount'] * d['qty'] for d in discounts)
        return subtotal + discount_total

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