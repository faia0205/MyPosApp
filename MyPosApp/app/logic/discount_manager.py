import json
import math
from typing import List, Dict, Tuple
from app.models.cart_item import CartItem

class DiscountManager:
    """割引計算ロジック（オブジェクト対応版）"""

    def calculate_discounts(self, cart_items: List[CartItem], rules: List[Dict]) -> List[Dict]:
        # 1. 計算用に在庫リストを作成 (Dict変換して管理)
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
        
        raw_discounts = []
        
        # 2. ルールの優先順位付け (変更なし)
        type_priority = {'bundle': 0, 'item': 1, 'category': 2, 'cart': 3}
        sorted_rules = sorted(rules, key=lambda r: (
            type_priority.get(r['apply_type'], 99),
            -r['discount_value'] 
        ))

        # 3. ルール適用 (ロジックは既存維持だが、カート合計計算だけ修正)
        for rule in sorted_rules:
            if not rule.get('is_auto', True): continue 

            apply_type = rule['apply_type']
            
            if apply_type == 'bundle':
                while True:
                    consumed, discount_amt = self._try_apply_bundle(rule, inventory)
                    if consumed and discount_amt > 0:
                        raw_discounts.append({
                            'rule_id': rule['id'],
                            'name': rule['name'],
                            'amount': -discount_amt,
                            'qty': 1
                        })
                    else:
                        break

            elif apply_type in ['item', 'category']:
                target = rule['target_value']
                for inv_item in inventory:
                    if inv_item['qty'] <= 0: continue
                    
                    is_hit = False
                    if apply_type == 'item' and inv_item['name'] == target: is_hit = True
                    elif apply_type == 'category' and inv_item['category'] == target: is_hit = True
                    
                    if is_hit:
                        count = inv_item['qty']
                        unit_discount = 0
                        if rule['discount_type'] == 'fixed':
                            unit_discount = rule['discount_value']
                        else:
                            unit_discount = math.floor(inv_item['price'] * (rule['discount_value'] / 100))
                        
                        if unit_discount > 0:
                            total_discount = unit_discount * count
                            raw_discounts.append({
                                'rule_id': rule['id'],
                                'name': rule['name'],
                                'amount': -total_discount,
                                'qty': count
                            })
                            inv_item['qty'] = 0

        # --- Cart全体割引 ---
        # CartItemオブジェクトから計算
        current_total = sum(item.price * item.qty for item in cart_items if item.price > 0)
        
        for rule in sorted_rules:
            if rule['apply_type'] == 'cart':
                disc = 0
                if rule['discount_type'] == 'fixed':
                    disc = rule['discount_value']
                else:
                    disc = math.floor(current_total * (rule['discount_value'] / 100))
                
                if disc > 0:
                    raw_discounts.append({
                        'rule_id': rule['id'],
                        'name': rule['name'],
                        'amount': -disc,
                        'qty': 1
                    })

        # 合算処理 (変更なし)
        merged_map = {}
        for d in raw_discounts:
            rid = d['rule_id']
            if rid in merged_map:
                merged_map[rid]['amount'] += d['amount']
                merged_map[rid]['qty'] += d['qty']
            else:
                merged_map[rid] = d.copy()

        return [v for v in merged_map.values() if v['amount'] < 0]

    def _try_apply_bundle(self, rule, inventory) -> Tuple[bool, int]:
        # 内部ロジックは inventory (dict list) を使うので変更不要
        try:
            target_json = json.loads(rule['target_value'])
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

        for idx, qty in temp_consumption.items():
            inventory[idx]['qty'] -= qty
            
        discount_amt = 0
        if rule['discount_type'] == 'fixed':
            discount_amt = rule['discount_value']
        else:
            discount_amt = math.floor(total_price_in_bundle * (rule['discount_value'] / 100))

        return True, discount_amt