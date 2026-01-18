from typing import List, Dict, Any, Tuple

class PriceCalculator:
    """
    価格計算、割引適用、利益予測を行う純粋なロジッククラス
    """

    def calculate_items_subtotal(self, items: List[Dict[str, Any]]) -> int:
        """商品の小計を計算 (割引を含まない純粋な商品合計)"""
        return sum(item['price'] * item['qty'] for item in items)

    def process_discounts(self, items: List[Dict[str, Any]], rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        現在のカート内容とルールに基づき、適用される割引リストを生成して返す
        Args:
            items: カート内の商品リスト
            rules: Repoから取得した割引ルール ({'id', 'name', 'req', 'amt', 'target_ids'})
        Returns:
            適用された割引のリスト [{'name', 'amount', 'qty'}]
        """
        applied_discounts = []

        for rule in rules:
            # 1. このルールの対象商品がカートにいくつあるか数える
            target_count = 0
            for item in items:
                # item['id'] が None (手入力) の場合は対象外
                if item['id'] is not None and item['id'] in rule['target_ids']:
                    target_count += item['qty']
            
            # 2. 適用回数を計算 (切り捨て)
            apply_times = target_count // rule['req']
            
            # 3. 適用されるならリストに追加
            if apply_times > 0:
                applied_discounts.append({
                    'name': rule['name'],
                    'amount': rule['amt'], # マイナス値
                    'qty': apply_times
                })
        
        return applied_discounts

    def calculate_grand_total(self, items: List[Dict], discounts: List[Dict]) -> int:
        """商品小計 + 割引合計 = 支払い総額"""
        subtotal = self.calculate_items_subtotal(items)
        discount_total = sum(d['amount'] * d['qty'] for d in discounts)
        return subtotal + discount_total

    def calculate_profit_metrics(self, current_total: int, total_sales_today: int, 
                                 current_expenses: int, avg_price_target: int) -> Tuple[int, bool, str]:
        """
        利益予測とメッセージを計算する
        Returns:
            (estimated_profit, is_red, message)
        """
        # 予想利益 = (確定売上 + 現在のカート) - 経費
        estimated_profit = (total_sales_today + current_total) - current_expenses
        
        is_red = False
        msg = "黒字達成!"
        
        if estimated_profit < 0:
            is_red = True
            # あと何個売ればいいか (0除算防止)
            target = avg_price_target if avg_price_target > 0 else 500
            needed = (abs(estimated_profit) // target) + 1
            msg = f"あと {needed} 個"
            
        return estimated_profit, is_red, msg