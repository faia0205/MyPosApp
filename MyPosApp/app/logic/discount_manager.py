import json
import math
from typing import List, Dict, Any, Tuple

class DiscountManager:
    """
    割引ルール（特にバンドルや自動適用）を計算し、結果をまとめるロジッククラス
    """

    def calculate_discounts(self, cart_items: List[Dict], rules: List[Dict]) -> List[Dict]:
        """
        カート内容とルールに基づき、適用される割引リストを返す。
        商品は「消費」され、二重適用を防ぐ（バンドル優先）。
        最後に同一ルールの割引を合算して返す。
        """
        # 1. 計算用にカートの中身を複製（残数管理用）
        # item['id'] をキーにして、残数(remaining_qty)を管理
        inventory = []
        for item in cart_items:
            # 手入力商品(id=None)や、すでに割引商品(price<0)の場合は対象外
            if item.get('id') is not None and item.get('price', 0) > 0:
                inventory.append({
                    'id': item['id'],
                    'name': item['name'],
                    'price': item['price'],
                    'category': self._get_category(item),
                    'qty': item['qty'], # この数量を減らしていく
                    'original_item': item
                })
        
        # 検出された割引を一旦ここに溜める（まだ合算しない）
        raw_discounts = []

        # 2. ルールの優先順位付け
        # 適用順序: バンドル(bundle) > 商品(item) > カテゴリ(category) > 全体(cart)
        # 同じタイプなら割引額が大きい順に適用して、お得な方を優先させる
        type_priority = {'bundle': 0, 'item': 1, 'category': 2, 'cart': 3}
        
        sorted_rules = sorted(rules, key=lambda r: (
            type_priority.get(r['apply_type'], 99),
            -r['discount_value'] 
        ))

        # 3. ルールごとに適用判定
        for rule in sorted_rules:
            # 今回は「ルールにあるものはすべて自動適用」として扱います
            # if not rule.get('is_auto', True): continue 

            apply_type = rule['apply_type']
            
            # --- C. セット割引 (Bundle) ---
            if apply_type == 'bundle':
                while True:
                    # 条件を満たすセットが作れるかチェックし、作れたら消費して割引追加
                    consumed, discount_amt = self._try_apply_bundle(rule, inventory)
                    if consumed and discount_amt > 0:
                        raw_discounts.append({
                            'rule_id': rule['id'],
                            'name': rule['name'],
                            'amount': -discount_amt, # マイナス金額
                            'qty': 1
                        })
                        # インベントリからの減算は _try_apply_bundle 内で実施済み
                    else:
                        break # これ以上このセットは作れない

            # --- A. 単品・カテゴリ割引 ---
            elif apply_type in ['item', 'category']:
                target = rule['target_value']
                
                for inv_item in inventory:
                    if inv_item['qty'] <= 0: continue
                    
                    is_hit = False
                    if apply_type == 'item' and inv_item['name'] == target:
                        is_hit = True
                    elif apply_type == 'category' and inv_item['category'] == target:
                        is_hit = True
                    
                    if is_hit:
                        count = inv_item['qty']
                        
                        # 割引額計算 (1個あたり)
                        unit_discount = 0
                        if rule['discount_type'] == 'fixed':
                            unit_discount = rule['discount_value']
                        else:
                            # %引き
                            unit_discount = math.floor(inv_item['price'] * (rule['discount_value'] / 100))
                        
                        if unit_discount > 0:
                            # 該当個数分すべて適用
                            total_discount = unit_discount * count
                            
                            raw_discounts.append({
                                'rule_id': rule['id'],
                                'name': rule['name'], # 商品名ではなくルール名でまとめる
                                'amount': -total_discount,
                                'qty': count
                            })
                            
                            # 在庫をすべて消費済みにする
                            inv_item['qty'] = 0

        # --- B. カート全体割引 (Cart) ---
        # アイテム消費とは関係なく、現在の合計金額に対して適用
        current_total = sum(item['price'] * item['qty'] for item in cart_items if item.get('price', 0) > 0)
        
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

        # ==========================================
        # ★追加機能: 同じルールの割引を合算(マージ)する
        # ==========================================
        merged_map = {} # { rule_id: {data} }

        for d in raw_discounts:
            rid = d['rule_id']
            if rid in merged_map:
                # 既存があれば加算
                merged_map[rid]['amount'] += d['amount'] # 金額を加算(マイナス同士の加算)
                merged_map[rid]['qty'] += d['qty']       # 回数を加算
            else:
                # 新規
                merged_map[rid] = d.copy()

        # 辞書からリストに戻して返す
        # 金額が0のものは除外
        result_list = [v for v in merged_map.values() if v['amount'] < 0]
        
        return result_list

    def _try_apply_bundle(self, rule, inventory) -> Tuple[bool, int]:
        """
        バンドル条件を満たすアイテムがインベントリにあるか探し、あれば減算して割引額を返す
        Returns: (成功したか, 割引額)
        """
        try:
            target_json = json.loads(rule['target_value'])
        except:
            return False, 0

        mode = target_json.get('mode', 'combo') # 'combo' or 'select'
        
        # 仮消費用の記録（失敗したらロールバックするため、まずは辞書に記録）
        temp_consumption = {} # { index: consume_qty }

        total_price_in_bundle = 0 # %割引計算用に、対象商品の合計額を計算

        if mode == 'select':
            # パターン1: 「対象群(A, B, C)から 合計N個」
            # 例: "たこ焼き、焼きそば、唐揚げ" から "2個"
            targets = target_json.get('targets', []) # 名前リスト
            required_qty = int(target_json.get('qty', 0))
            current_picked = 0
            
            # インベントリを走査して対象商品を集める
            for idx, item in enumerate(inventory):
                # 既に消費予定分(temp_consumption)を引いた残りで判定
                remaining = item['qty'] - temp_consumption.get(idx, 0)
                
                if remaining > 0 and (item['name'] in targets or item['category'] in targets):
                    # 必要な分だけ取る
                    take = min(remaining, required_qty - current_picked)
                    if take > 0:
                        temp_consumption[idx] = temp_consumption.get(idx, 0) + take
                        current_picked += take
                        total_price_in_bundle += item['price'] * take
                    
                    if current_picked >= required_qty:
                        break
            
            if current_picked < required_qty:
                return False, 0 # 足りない

        elif mode == 'combo':
            # パターン2: 「Aを1個 と Bを1個」 (厳密な組み合わせ)
            conditions = target_json.get('conditions', []) # [{target:.., type:.., qty:..}]
            
            for cond in conditions:
                cond_target = cond['target']
                cond_type = cond.get('type', 'item')
                cond_qty = int(cond.get('qty', 1))
                
                needed = cond_qty
                
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
                
                if needed > 0:
                    return False, 0 # この条件を満たせなかった

        # ここまで到達 = 条件成立。実際にインベントリから減算する
        for idx, qty in temp_consumption.items():
            inventory[idx]['qty'] -= qty
            
        # 割引額決定
        discount_amt = 0
        if rule['discount_type'] == 'fixed':
            discount_amt = rule['discount_value']
        else:
            # %引きの場合、バンドル対象商品の合計金額に対して掛ける
            discount_amt = math.floor(total_price_in_bundle * (rule['discount_value'] / 100))

        return True, discount_amt

    def _get_category(self, item_dict):
        """商品のカテゴリを取得（カート情報に含まれている前提）"""
        return item_dict.get('category', 'その他')