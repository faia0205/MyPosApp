import math
from typing import List, Dict
from app.logic.strategies.discount_strategy import DiscountStrategy
from app.models.discount import DiscountRule, AppliedDiscount

class CategoryDiscountStrategy(DiscountStrategy):
    """特定のカテゴリに対する割引ロジック"""

    def apply(self, inventory: List[Dict], rule: DiscountRule, current_net_total: int = 0) -> List[AppliedDiscount]:
        applied = []
        target_category = rule.target_value # 対象のカテゴリ名
        
        for inv_item in inventory:
            if inv_item['qty'] <= 0:
                continue
            
            if inv_item['category'] == target_category:
                count = inv_item['qty']
                unit_discount = 0
                
                if rule.discount_type == 'fixed':
                    unit_discount = rule.discount_value
                else:
                    unit_discount = math.floor(inv_item['price'] * (rule.discount_value / 100))
                
                if unit_discount > 0:
                    total_discount = unit_discount * count
                    
                    applied.append(AppliedDiscount(
                        rule_id=rule.id,
                        name=rule.name,
                        amount=-total_discount,
                        qty=count
                    ))
                    
                    # 在庫消費
                    inv_item['qty'] = 0
                    
        return applied