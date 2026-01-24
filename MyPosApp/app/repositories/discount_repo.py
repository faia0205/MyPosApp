from typing import List, Optional
from app.repositories.base_repo import BaseRepository
from app.models.discount import DiscountRule

class DiscountRepository(BaseRepository):
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
    
    # 以前の add_rule / update_rule は廃止し、add / update に統合しました。

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