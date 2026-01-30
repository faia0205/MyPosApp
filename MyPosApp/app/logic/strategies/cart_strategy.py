import math
from typing import List, Dict
from app.logic.strategies.discount_strategy import DiscountStrategy
from app.models.discount import DiscountRule, AppliedDiscount

class CartDiscountStrategy(DiscountStrategy):
    """
    カート合計に対する割引ロジック
    他の割引が適用された後の「小計 (current_net_total)」に対して計算を行う。
    """

    def apply(self, inventory: List[Dict], rule: DiscountRule, current_net_total: int = 0) -> List[AppliedDiscount]:
        discount_amt = 0
        
        if rule.discount_type == 'fixed':
            discount_amt = rule.discount_value
        else:
            # 小計に対するパーセンテージ
            discount_amt = math.floor(current_net_total * (rule.discount_value / 100))

        # 計算結果が0より大きければ適用候補として返す
        # ※ 最終的なマイナスチェック（割引額 > 合計額）はManager側で制御されるが、
        #    ここでは純粋な計算値を返却する。
        if discount_amt > 0:
            return [AppliedDiscount(
                rule_id=rule.id,
                name=rule.name,
                amount=-discount_amt, # 負の値
                qty=1
            )]
            
        return []