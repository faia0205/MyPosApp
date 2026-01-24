import json
import math
from typing import List, Dict, Tuple
from app.models.cart_item import CartItem
from app.models.discount import DiscountRule, AppliedDiscount

class DiscountManager:
    """割引計算ロジック（オブジェクト対応版）"""

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

            apply_type = rule.apply_type
            
            # --- カート全体割引は後回しにする ---
            if apply_type == 'cart':
                continue

            if apply_type == 'bundle':
                while True:
                    consumed, discount_amt = self._try_apply_bundle(rule, inventory)
                    if consumed and discount_amt > 0:
                        applied_discounts.append(AppliedDiscount(
                            rule_id=rule.id,
                            name=rule.name,
                            amount=-discount_amt,
                            qty=1
                        ))
                    else:
                        break

            elif apply_type in ['item', 'category']:
                target = rule.target_value
                for inv_item in inventory:
                    if inv_item['qty'] <= 0: continue
                    
                    is_hit = False
                    if apply_type == 'item' and inv_item['name'] == target: is_hit = True
                    elif apply_type == 'category' and inv_item['category'] == target: is_hit = True
                    
                    if is_hit:
                        count = inv_item['qty']
                        unit_discount = 0
                        
                        if rule.discount_type == 'fixed':
                            unit_discount = rule.discount_value
                        else:
                            unit_discount = math.floor(inv_item['price'] * (rule.discount_value / 100))
                        
                        if unit_discount > 0:
                            total_discount = unit_discount * count
                            applied_discounts.append(AppliedDiscount(
                                rule_id=rule.id,
                                name=rule.name,
                                amount=-total_discount,
                                qty=count
                            ))
                            inv_item['qty'] = 0

        # --- 4. Cart全体割引の計算 ---
        # ★修正ポイント: ここまでの割引適用後の金額（Net Total）をベースにする
        
        # 定価ベースの合計
        gross_total = sum(item.price * item.qty for item in cart_items if item.price > 0)
        
        # 適用済み割引の合計 (amountは負の値なので足し込むと引かれる)
        discount_sum_so_far = sum(d.amount for d in applied_discounts)
        
        # 割引適用後の小計 (0未満にはならない)
        net_total = max(0, gross_total + discount_sum_so_far)

        for rule in sorted_rules:
            if rule.apply_type == 'cart':
                if not rule.is_auto: continue
                
                disc = 0
                if rule.discount_type == 'fixed':
                    disc = rule.discount_value
                else:
                    # ★修正: 定価(gross_total)ではなく、割引後小計(net_total)に対して率を掛ける
                    disc = math.floor(net_total * (rule.discount_value / 100))
                
                # 割引額が有効、かつ小計を超えない範囲で適用
                if disc > 0:
                    # 念のため、残りの金額以上には割り引かない（マイナス会計防止）
                    # 複数のカート割引がある場合、並列適用の場合は net_total を使うが、
                    # 累積適用の場合はここでも net_total を減算していく必要がある。
                    # ここでは「並列適用（Net Totalに対する率）」とするが、最大額チェックを入れる。
                    
                    # 現在の残額チェック
                    current_discount_total = sum(d.amount for d in applied_discounts) # 再計算
                    current_remaining = max(0, gross_total + current_discount_total)
                    
                    final_disc = min(disc, current_remaining)

                    if final_disc > 0:
                        applied_discounts.append(AppliedDiscount(
                            rule_id=rule.id,
                            name=rule.name,
                            amount=-final_disc,
                            qty=1
                        ))

        # 5. 合算処理 (AppliedDiscountオブジェクト同士をマージ)
        merged_map: Dict[int, AppliedDiscount] = {}
        for d in applied_discounts:
            rid = d.rule_id
            if rid in merged_map:
                merged_map[rid].amount += d.amount
                merged_map[rid].qty += d.qty
            else:
                merged_map[rid] = d

        return list(merged_map.values())

    def _try_apply_bundle(self, rule: DiscountRule, inventory: List[Dict]) -> Tuple[bool, int]:
        try:
            target_json = json.loads(rule.target_value)
        except:
            return False, 0

        mode = target_json.get('mode', 'combo')
        temp_consumption = {} 
        total_price_in_bundle = 0

        if mode == 'select':
            targets = target_json.get('targets', [])
            required_qty = int(target_json.get('qty', 0))
            current_picked = 0
            
            for idx, item in enumerate(inventory):
                remaining = item['qty'] - temp_consumption.get(idx, 0)
                if remaining > 0 and (item['name'] in targets or item['category'] in targets):
                    take = min(remaining, required_qty - current_picked)
                    if take > 0:
                        temp_consumption[idx] = temp_consumption.get(idx, 0) + take
                        current_picked += take
                        total_price_in_bundle += item['price'] * take
                    if current_picked >= required_qty: break
            
            if current_picked < required_qty: return False, 0

        elif mode == 'combo':
            conditions = target_json.get('conditions', [])
            for cond in conditions:
                cond_target = cond['target']
                cond_type = cond.get('type', 'item')
                needed = int(cond.get('qty', 1))
                
                for idx, item in enumerate(inventory):
                    remaining = item['qty'] - temp_consumption.get(idx, 0)
                    if remaining > 0:
                        is_match = False
                        if cond_type == 'item' and item['name'] == cond_target: is_match = True
                        elif cond_type == 'category' and item['category'] == cond_target: is_match = True
                        
                        if is_match:
                            take = min(remaining, needed)
                            temp_consumption[idx] = temp_consumption.get(idx, 0) + take
                            needed -= take
                            total_price_in_bundle += item['price'] * take
                    if needed <= 0: break
                
                if needed > 0: return False, 0

        # 消費確定
        for idx, qty in temp_consumption.items():
            inventory[idx]['qty'] -= qty
            
        discount_amt = 0
        if rule.discount_type == 'fixed':
            discount_amt = rule.discount_value
        else:
            discount_amt = math.floor(total_price_in_bundle * (rule.discount_value / 100))

        return True, discount_amt