from typing import List, Optional, Dict
from app.repositories.base_repo import BaseRepository
from app.models.discount import DiscountRule
from app.repositories.interfaces.master_data_repo import IMasterDataRepository

class DiscountRepository(BaseRepository, IMasterDataRepository):
    """割引ルールのCRUD (Dataclass対応版)"""

    def fetch_all_rules(self) -> List[DiscountRule]:
        """設定画面用: 全ルール取得"""
        with self.transaction() as (conn, cursor):
            cursor.execute("""
                SELECT id, name, discount_type, discount_value, apply_type, target_value, is_auto, is_active 
                FROM discount_rules 
                ORDER BY id
            """)
            rows = cursor.fetchall()
            return [self._map_to_model(row) for row in rows]

    def fetch_active_rules(self) -> List[DiscountRule]:
        """販売画面用: 有効なルールのみ取得"""
        with self.transaction() as (conn, cursor):
            cursor.execute("""
                SELECT id, name, discount_type, discount_value, apply_type, target_value, is_auto, is_active 
                FROM discount_rules 
                WHERE is_active=1
            """)
            rows = cursor.fetchall()
            return [self._map_to_model(row) for row in rows]

    def add(self, rule: DiscountRule) -> bool:
        """ルールの追加"""
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("""
                    INSERT INTO discount_rules (name, discount_type, discount_value, apply_type, target_value, is_auto, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule.name, 
                    rule.discount_type, 
                    rule.discount_value, 
                    rule.apply_type, 
                    rule.target_value, 
                    int(rule.is_auto), 
                    int(rule.is_active)
                ))
            return True
        except Exception as e:
            print(f"Error adding discount rule: {e}")
            return False

    def update(self, rule: DiscountRule) -> bool:
        """ルールの更新"""
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("""
                    UPDATE discount_rules 
                    SET name=?, discount_type=?, discount_value=?, apply_type=?, target_value=?, is_auto=?, is_active=?
                    WHERE id=?
                """, (
                    rule.name, 
                    rule.discount_type, 
                    rule.discount_value, 
                    rule.apply_type, 
                    rule.target_value, 
                    int(rule.is_auto), 
                    int(rule.is_active), 
                    rule.id
                ))
            return True
        except Exception as e:
            print(f"Error updating discount rule: {e}")
            return False

    def _map_to_model(self, row) -> DiscountRule:
        if row is None: return None
        return DiscountRule(
            id=row[0],
            name=row[1],
            discount_type=row[2],
            discount_value=row[3],
            apply_type=row[4],
            target_value=row[5] if row[5] else "",
            is_auto=bool(row[6]),
            is_active=bool(row[7])
        )
    
    def delete(self, rule_id: int) -> bool:
        """物理削除"""
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("DELETE FROM discount_rules WHERE id=?", (rule_id,))
            return True
        except Exception as e:
            print(f"Error deleting discount rule: {e}")
            return False
    
    def import_data(self, data: Dict) -> bool:
        """辞書データを取り込み"""
        try:
            rule = DiscountRule.from_dict(data)
            if rule.id:
                if self.update(rule):
                    return True
            return self.add(rule)
        except Exception as e:
            print(f"Error importing discount rule: {e}")
            return False
    
    def get_master_key(self) -> str:
        return "discount_rules"

    def export_all_data(self) -> List[Dict]:
        # モデルを取得して辞書化する既存ロジックをラップ
        models = self.fetch_all_rules()
        return [p.to_dict() for p in models]

    def import_all_data(self, data_list: List[Dict]) -> bool:
        success = True
        for data in data_list:
            if not self.import_data(data):
                success = False
        return success
    
    def delete_not_in(self, active_ids: List[int]) -> None:
        """JSONにないIDの割引ルールを削除"""
        try:
            with self.transaction() as (conn, cursor):
                if not active_ids:
                    cursor.execute("DELETE FROM discount_rules")
                    print("[Discount] Deleted ALL rules (JSON empty).")
                else:
                    placeholders = ','.join(['?'] * len(active_ids))
                    sql = f"DELETE FROM discount_rules WHERE id NOT IN ({placeholders})"
                    cursor.execute(sql, active_ids)
                    
                    if cursor.rowcount > 0:
                        print(f"[Discount] Deleted {cursor.rowcount} rules not in JSON.")
        except Exception as e:
            print(f"Error executing Discount delete_not_in: {e}")