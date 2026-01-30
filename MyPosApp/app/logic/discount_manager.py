import math
from typing import List, Dict
from app.models.cart_item import CartItem
from app.models.discount import DiscountRule, AppliedDiscount
from app.logic.strategies.discount_strategy import DiscountStrategy

class DiscountManager:
    """割引計算ロジック（Strategyパターン適用版）"""

    def __init__(self, strategies: Dict[str, DiscountStrategy]):
        self.strategies = strategies

    def calculate_discounts(self, cart_items: List[CartItem], rules: List[DiscountRule]) -> List[AppliedDiscount]:
        # 1. 計算用に在庫リストを作成
        inventory = []
        for item in cart_items:
            if item.id is not None and item.price > 0:
                inventory.append({
                    'id': item.id,
                    'name': item.name,
                    'price': item.price,
                    'category': item.category,
                    'qty': item.qty,
                    'original_item': item
                })

        applied_discounts: List[AppliedDiscount] = []

        # 2. ルールの優先順位付け (バンドル > 商品 > カテゴリ > 全体)
        type_priority = {'bundle': 0, 'item': 1, 'category': 2, 'cart': 3}
        sorted_rules = sorted(rules, key=lambda r: (
            type_priority.get(r.apply_type, 99),
            -r.discount_value
        ))

        # 3. ルール適用（バンドル・商品・カテゴリ）
        for rule in sorted_rules:
            if not rule.is_auto: continue
            
            # カート全体割引は後回し
            if rule.apply_type == 'cart':
                continue

            # Strategyの取得と実行
            strategy = self.strategies.get(rule.apply_type)
            if strategy:
                results = strategy.apply(inventory, rule)
                applied_discounts.extend(results)

        # 4. Cart全体割引の計算
        gross_total = sum(item.price * item.qty for item in cart_items if item.price > 0)
        discount_sum_so_far = sum(d.amount for d in applied_discounts)
        net_total = max(0, gross_total + discount_sum_so_far)

        cart_strategy = self.strategies.get('cart')
        if cart_strategy:
            for rule in sorted_rules:
                if rule.apply_type == 'cart' and rule.is_auto:
                    results = cart_strategy.apply(inventory, rule, current_net_total=net_total)
                    
                    for res in results:
                        current_disc_total = sum(d.amount for d in applied_discounts)
                        current_remaining = max(0, gross_total + current_disc_total)
                        
                        actual_disc = min(abs(res.amount), current_remaining)
                        if actual_disc > 0:
                            res.amount = -actual_disc
                            applied_discounts.append(res)
                            net_total = max(0, net_total - actual_disc)

        # 5. 合算処理
        merged_map: Dict[int, AppliedDiscount] = {}
        for d in applied_discounts:
            rid = d.rule_id
            if rid in merged_map:
                merged_map[rid].amount += d.amount
                merged_map[rid].qty += d.qty
            else:
                merged_map[rid] = d

        return list(merged_map.values())