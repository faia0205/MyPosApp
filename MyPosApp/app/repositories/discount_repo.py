from typing import List, Dict, Any
import sqlite3
from app.repositories.base_repo import BaseRepository

class DiscountRepository(BaseRepository):
    """割引ルールのCRUD"""

    def fetch_all_rules(self) -> List[Dict[str, Any]]:
        """設定画面用: 全ルール取得"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, discount_type, discount_value, apply_type, target_value, is_auto, is_active 
            FROM discount_rules 
            ORDER BY id
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def fetch_active_rules(self) -> List[Dict[str, Any]]:
        """販売画面用: 有効なルールのみ取得"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, discount_type, discount_value, apply_type, target_value 
            FROM discount_rules 
            WHERE is_active=1
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_rule(self, name, d_type, d_value, a_type, target, is_auto) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO discount_rules (name, discount_type, discount_value, apply_type, target_value, is_auto, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (name, d_type, int(d_value), a_type, target, int(is_auto)))
            conn.commit()
            return True
        except: return False
        finally: conn.close()

    def update_rule(self, rule_id, name, d_type, d_value, a_type, target, is_auto, is_active) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE discount_rules 
                SET name=?, discount_type=?, discount_value=?, apply_type=?, target_value=?, is_auto=?, is_active=?
                WHERE id=?
            """, (name, d_type, int(d_value), a_type, target, int(is_auto), int(is_active), rule_id))
            conn.commit()
            return True
        except: return False
        finally: conn.close()