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
        gross_total = 0
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
                gross_total += item.price * item.qty

        applied_discounts: List[AppliedDiscount] = []

        # 2. ルールの優先順位付け (バンドル > 商品 > カテゴリ > 全体)
        def get_sort_key(rule: DiscountRule):
            strategy = self.strategies.get(rule.apply_type)
            if not strategy:
                # 戦略が見つからない場合は最後尾へ
                return (999, 999, 0)
            return (strategy.phase, strategy.priority, -rule.discount_value)

        sorted_rules = sorted(rules, key=get_sort_key)

        # 3. ルール適用（バンドル・商品・カテゴリ）
        for rule in sorted_rules:
            if not rule.is_auto: continue
            
            strategy = self.strategies.get(rule.apply_type)
            if not strategy: continue

            # コンテキスト準備
            current_net_total = 0
            
            # POSTフェーズの場合のみ、現在の小計を計算して渡す
            if strategy.phase == DiscountStrategy.PHASE_POST:
                discount_sum_so_far = sum(d.amount for d in applied_discounts)
                current_net_total = max(0, gross_total + discount_sum_so_far)

            # Strategy実行
            results = strategy.apply(inventory, rule, current_net_total=current_net_total)

            # POSTフェーズの場合は、割引額が残高を超えないよう調整 (Capping)
            if strategy.phase == DiscountStrategy.PHASE_POST and results:
                # 再計算（念のため最新の状態を取得）
                discount_sum_so_far = sum(d.amount for d in applied_discounts)
                remaining = max(0, gross_total + discount_sum_so_far)
                
                valid_results = []
                for res in results:
                    actual_disc = min(abs(res.amount), remaining)
                    if actual_disc > 0:
                        res.amount = -actual_disc
                        valid_results.append(res)
                        remaining -= actual_disc
                
                applied_discounts.extend(valid_results)
            else:
                # STANDARDフェーズはそのまま追加
                applied_discounts.extend(results)

        # 4. 合算処理
        merged_map: Dict[int, AppliedDiscount] = {}
        for d in applied_discounts:
            rid = d.rule_id
            if rid in merged_map:
                merged_map[rid].amount += d.amount
                merged_map[rid].qty += d.qty
            else:
                merged_map[rid] = d

        return list(merged_map.values())