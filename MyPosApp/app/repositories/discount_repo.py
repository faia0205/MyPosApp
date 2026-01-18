from typing import List, Dict, Any
from app.repositories.base_repo import BaseRepository

class DiscountRepository(BaseRepository):
    def fetch_rules_with_targets(self) -> List[Dict[str, Any]]:
        """
        有効な割引ルールと、その対象商品IDリストを取得する
        戻り値例: [
            {
                'id': 1, 'name': 'セット割', 'req': 2, 'amt': -50,
                'target_ids': {1, 2, 3}  # set型で高速化
            }, ...
        ]
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. ルール取得
        cursor.execute("SELECT id, name, required_qty, discount_amount FROM discount_rules WHERE is_active=1")
        rules = []
        for r in cursor.fetchall():
            rules.append({
                'id': r[0], 'name': r[1], 'req': r[2], 'amt': r[3],
                'target_ids': set() # 空のセットを用意
            })
            
        # 2. 対象商品取得
        for rule in rules:
            cursor.execute("SELECT product_id FROM discount_targets WHERE rule_id=?", (rule['id'],))
            rows = cursor.fetchall()
            rule['target_ids'] = {row[0] for row in rows} # IDをセットに格納
            
        conn.close()
        return rules