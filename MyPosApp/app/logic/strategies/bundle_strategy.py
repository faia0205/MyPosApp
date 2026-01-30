import json
import math
from typing import List, Dict, Tuple
from app.logic.strategies.discount_strategy import DiscountStrategy
from app.models.discount import DiscountRule, AppliedDiscount

class BundleDiscountStrategy(DiscountStrategy):
    """
    バンドル（セット）割引ロジック
    JSON形式の target_value を解析し、条件に合う組み合わせがある限り適用を繰り返す。
    """

    def apply(self, inventory: List[Dict], rule: DiscountRule, current_net_total: int = 0) -> List[AppliedDiscount]:
        applied = []
        
        # 可能な限りセットを作成し続ける
        while True:
            # 1セット分の適用を試みる
            consumed, discount_amt = self._try_apply_bundle(rule, inventory)
            
            if consumed and discount_amt > 0:
                applied.append(AppliedDiscount(
                    rule_id=rule.id,
                    name=rule.name,
                    amount=-discount_amt,
                    qty=1 # 1セット分
                ))
            else:
                # これ以上セットが作れなければ終了
                break
                
        return applied

    def _try_apply_bundle(self, rule: DiscountRule, inventory: List[Dict]) -> Tuple[bool, int]:
        """
        在庫から1セット分の商品を確保できるかチェックし、確保できれば在庫を減らして割引額を返す。
        Returns: (成功フラグ, 割引額)
        """
        try:
            target_json = json.loads(rule.target_value)
        except Exception:
            return False, 0

        mode = target_json.get('mode', 'combo')
        
        # 仮の消費記録（インデックス: 消費数）
        # まだ確定ではないので一時辞書に記録する
        temp_consumption = {}
        total_price_in_bundle = 0 # ％割引計算用に対象商品の合計額を算出

        # --- パターンA: 選択式 (例: 対象商品A, B, C から好きなものを3個) ---
        if mode == 'select':
            targets = target_json.get('targets', []) # 対象の商品名またはカテゴリ名のリスト
            required_qty = int(target_json.get('qty', 0))
            current_picked = 0
            
            for idx, item in enumerate(inventory):
                # 既にこの試行で消費予定の分を除いた残数
                remaining = item['qty'] - temp_consumption.get(idx, 0)
                
                # 対象リストに含まれているか (名前 or カテゴリ)
                if remaining > 0 and (item['name'] in targets or item['category'] in targets):
                    # 必要数まで取得
                    take = min(remaining, required_qty - current_picked)
                    if take > 0:
                        temp_consumption[idx] = temp_consumption.get(idx, 0) + take
                        current_picked += take
                        total_price_in_bundle += item['price'] * take
                    
                    if current_picked >= required_qty:
                        break
            
            # 数が足りなければ失敗
            if current_picked < required_qty:
                return False, 0

        # --- パターンB: 組み合わせ (例: 商品Aを1個 ＋ カテゴリBを2個) ---
        elif mode == 'combo':
            conditions = target_json.get('conditions', [])
            
            for cond in conditions:
                cond_target = cond['target'] # 名前またはカテゴリ名
                cond_type = cond.get('type', 'item') # 'item' or 'category'
                needed = int(cond.get('qty', 1))
                
                # 在庫を走査して必要な分を集める
                for idx, item in enumerate(inventory):
                    remaining = item['qty'] - temp_consumption.get(idx, 0)
                    if remaining > 0:
                        is_match = False
                        if cond_type == 'item' and item['name'] == cond_target:
                            is_match = True
                        elif cond_type == 'category' and item['category'] == cond_target:
                            is_match = True
                        
                        if is_match:
                            take = min(remaining, needed)
                            temp_consumption[idx] = temp_consumption.get(idx, 0) + take
                            needed -= take
                            total_price_in_bundle += item['price'] * take
                            
                            if needed <= 0:
                                break
                
                # 条件を一つでも満たせなければ失敗
                if needed > 0:
                    return False, 0

        # --- 確定処理 ---
        # ここまで到達したらセット成立。実際に在庫(inventory)を減らす
        for idx, qty in temp_consumption.items():
            inventory[idx]['qty'] -= qty

        # 割引額の計算
        discount_amt = 0
        if rule.discount_type == 'fixed':
            discount_amt = rule.discount_value
        else:
            # 対象商品の合計金額に対する割合
            discount_amt = math.floor(total_price_in_bundle * (rule.discount_value / 100))

        return True, discount_amt