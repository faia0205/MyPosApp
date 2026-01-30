import math
from typing import List, Dict
from app.logic.strategies.discount_strategy import DiscountStrategy
from app.models.discount import DiscountRule, AppliedDiscount

class ItemDiscountStrategy(DiscountStrategy):
    """特定の商品に対する割引ロジック"""

    def apply(self, inventory: List[Dict], rule: DiscountRule, current_net_total: int = 0) -> List[AppliedDiscount]:
        applied = []
        target_name = rule.target_value # 対象の商品名
        
        for inv_item in inventory:
            # 在庫がない、または対象外の商品はスキップ
            if inv_item['qty'] <= 0:
                continue
            
            if inv_item['name'] == target_name:
                count = inv_item['qty']
                unit_discount = 0
                
                # 割引額の計算
                if rule.discount_type == 'fixed':
                    unit_discount = rule.discount_value
                else:
                    # %割引 (端数は切り捨て)
                    unit_discount = math.floor(inv_item['price'] * (rule.discount_value / 100))
                
                if unit_discount > 0:
                    total_discount = unit_discount * count
                    
                    applied.append(AppliedDiscount(
                        rule_id=rule.id,
                        name=rule.name,
                        amount=-total_discount, # 割引額は負の値
                        qty=count
                    ))
                    
                    # 計算上の在庫を全て消費済みにする
                    inv_item['qty'] = 0
                    
        return applied