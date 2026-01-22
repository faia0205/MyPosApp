import json
from typing import List, Dict, Any, Tuple
import math

class DiscountManager:
    """
    複雑な割引ルール（バンドル、セット、自動適用）を計算するロジッククラス
    """

    def calculate_discounts(self, cart_items: List[Dict], rules: List[Dict]) -> List[Dict]:
        """
        カート内容とルールに基づき、適用される割引リストを返す。
        商品は「消費」され、二重適用を防ぐ（バンドル優先）。
        """
        # 1. 計算用にカートの中身を複製（残数管理用）
        # item['id'] をキーにして、残数(remaining_qty)を管理
        # 手入力商品(id=None)や割引行(price<0)は対象外とする
        inventory = []
        for item in cart_items:
            if item.get('id') is not None and item.get('price', 0) > 0:
                inventory.append({
                    'id': item['id'],
                    'name': item['name'],
                    'price': item['price'],
                    'category': self._get_category(item), # ※後述
                    'qty': item['qty'],
                    'original_item': item
                })
        
        applied_discounts = []

        # 2. ルールの優先順位付け
        # バンドル(bundle) > 商品(item) > カテゴリ(category) の順で適用
        # 同じタイプなら割引額が大きい順
        sorted_rules = sorted(rules, key=lambda r: (
            0 if r['apply_type'] == 'bundle' else 1 if r['apply_type'] == 'item' else 2,
            -r['discount_value'] # 金額が高い順
        ))

        # 3. ルールごとに適用判定
        for rule in sorted_rules:
            if not rule['is_auto']: continue # 自動適用のみ

            apply_type = rule['apply_type']
            
            # --- C. セット割引 (Bundle) ---
            if apply_type == 'bundle':
                while True:
                    # 条件を満たすセットが作れるかチェックし、作れたら消費して割引追加
                    consumed, discount_amt = self._try_apply_bundle(rule, inventory)
                    if consumed:
                        applied_discounts.append({
                            'name': rule['name'],
                            'amount': -discount_amt,
                            'qty': 1,
                            'rule_id': rule['id']
                        })
                        # インベントリから減算（_try_apply_bundle内で実施済み）
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
                        # 適用可能な個数
                        count = inv_item['qty']
                        
                        # 割引額計算
                        unit_discount = 0
                        if rule['discount_type'] == 'fixed':
                            unit_discount = rule['discount_value']
                        else:
                            unit_discount = math.floor(inv_item['price'] * (rule['discount_value'] / 100))
                        
                        if unit_discount > 0:
                            applied_discounts.append({
                                'name': f"{rule['name']} ({inv_item['name']})",
                                'amount': -unit_discount,
                                'qty': count,
                                'rule_id': rule['id']
                            })
                            # 全て消費
                            inv_item['qty'] = 0

        # --- B. カート全体割引 (Cart) ---
        # アイテム消費とは関係なく、現在の合計金額に対して適用
        # ※ここでの合計は「商品合計 - 上記の割引合計」とするか「商品定価合計」とするかは仕様次第
        # 今回は「商品定価合計」に対して適用します
        current_total = sum(item['price'] * item['qty'] for item in cart_items if item.get('price', 0) > 0)
        
        for rule in rules:
            if not rule['is_auto']: continue
            if rule['apply_type'] == 'cart':
                disc = 0
                if rule['discount_type'] == 'fixed':
                    disc = rule['discount_value']
                else:
                    disc = math.floor(current_total * (rule['discount_value'] / 100))
                
                if disc > 0:
                    applied_discounts.append({
                        'name': rule['name'],
                        'amount': -disc,
                        'qty': 1,
                        'rule_id': rule['id']
                    })

        return applied_discounts

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
        
        # 仮消費用のコピーを作成（失敗したらロールバックするため）
        # 簡易的に、inventoryリスト内の辞書の 'qty' を一時的に減らすシミュレーションを行う
        temp_consumption = {} # { index: consume_qty }

        total_price_in_bundle = 0 # %割引計算用

        if mode == 'select':
            # 「対象群(A, B, C)から N個」パターン
            targets = target_json.get('targets', []) # 名前リスト
            required_qty = int(target_json.get('qty', 0))
            current_picked = 0
            
            # インベントリを走査して対象商品を集める
            for idx, item in enumerate(inventory):
                if item['qty'] > 0 and (item['name'] in targets or item['category'] in targets):
                    # 必要な分だけ取る
                    take = min(item['qty'], required_qty - current_picked)
                    if take > 0:
                        temp_consumption[idx] = temp_consumption.get(idx, 0) + take
                        current_picked += take
                        total_price_in_bundle += item['price'] * take
                    
                    if current_picked >= required_qty:
                        break
            
            if current_picked < required_qty:
                return False, 0 # 足りない

        elif mode == 'combo':
            # 「Aを1個 と Bを1個」パターン
            conditions = target_json.get('conditions', []) # [{target:.., type:.., qty:..}]
            
            for cond in conditions:
                cond_target = cond['target']
                cond_type = cond.get('type', 'item')
                cond_qty = int(cond.get('qty', 1))
                
                needed = cond_qty
                
                for idx, item in enumerate(inventory):
                    if item['qty'] - temp_consumption.get(idx, 0) > 0:
                        is_match = False
                        if cond_type == 'item' and item['name'] == cond_target: is_match = True
                        elif cond_type == 'category' and item['category'] == cond_target: is_match = True
                        
                        if is_match:
                            available = item['qty'] - temp_consumption.get(idx, 0)
                            take = min(available, needed)
                            temp_consumption[idx] = temp_consumption.get(idx, 0) + take
                            needed -= take
                            total_price_in_bundle += item['price'] * take
                    
                    if needed <= 0: break
                
                if needed > 0:
                    return False, 0 # この条件を満たせなかった

        # ここまで来たら成立。実際に消費する
        for idx, qty in temp_consumption.items():
            inventory[idx]['qty'] -= qty
            
        # 割引額決定
        discount_amt = 0
        if rule['discount_type'] == 'fixed':
            discount_amt = rule['discount_value']
        else:
            discount_amt = math.floor(total_price_in_bundle * (rule['discount_value'] / 100))

        return True, discount_amt

    def _get_category(self, item_dict):
        """
        カートアイテムにはカテゴリ情報がない場合が多いので、
        必要ならRepoから引くか、カート追加時にカテゴリ情報を付与する設計にすべき。
        今回は、cart_service側で category を付与するように修正するか、
        ここでProductRepositoryを呼ぶ。
        パフォーマンスのため、CartService側で item['category'] を持たせる方針とします。
        （持っていなければ "その他" 扱い）
        """
        return item_dict.get('category', 'その他')