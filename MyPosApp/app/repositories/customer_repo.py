from typing import List, Dict, Optional
import json
from app.repositories.base_repo import BaseRepository
from app.models.customer import Customer

class CustomerRepository(BaseRepository):
    """客層データのCRUD（Dataclass対応版）"""

    def fetch_all(self) -> List[Customer]:
        """設定画面・JSON出力用: 全ての客層を取得"""
        with self.transaction() as (conn, cursor):
            cursor.execute("""
                SELECT id, label, attributes, color, display_order, is_active 
                FROM customer_presets 
                ORDER BY display_order
            """)
            rows = cursor.fetchall()
            return [self._map_to_model(row) for row in rows]

    def fetch_active(self) -> List[Customer]:
        """販売画面用: 有効な客層のみを取得"""
        with self.transaction() as (conn, cursor):
            cursor.execute("""
                SELECT id, label, attributes, color, display_order, is_active 
                FROM customer_presets 
                WHERE is_active=1 
                ORDER BY display_order
            """)
            rows = cursor.fetchall()
            return [self._map_to_model(row) for row in rows]

    def add(self, customer: Customer) -> bool:
        """新規追加"""
        try:
            with self.transaction() as (conn, cursor):
                # 最大並び順取得
                cursor.execute("SELECT MAX(display_order) FROM customer_presets")
                res = cursor.fetchone()
                max_ord = res[0] if res and res[0] is not None else 0
                
                cursor.execute("""
                    INSERT INTO customer_presets (label, attributes, color, display_order, is_active)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    customer.label, 
                    customer.attributes_json, 
                    customer.color, 
                    max_ord + 1, 
                    int(customer.is_active)
                ))
            return True
        except Exception as e:
            print(f"Error adding customer: {e}")
            return False

    def update(self, customer: Customer) -> bool:
        """更新"""
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("""
                    UPDATE customer_presets 
                    SET label=?, attributes=?, color=?, is_active=?
                    WHERE id=?
                """, (
                    customer.label, 
                    customer.attributes_json, 
                    customer.color, 
                    int(customer.is_active), 
                    customer.id
                ))
            return True
        except Exception as e:
            print(f"Error updating customer: {e}")
            return False

    def update_display_order(self, order_map: Dict[int, int]) -> bool:
        """並び順更新"""
        try:
            with self.transaction() as (conn, cursor):
                for pid, order in order_map.items():
                    cursor.execute("UPDATE customer_presets SET display_order=? WHERE id=?", (order, pid))
            return True
        except Exception as e:
            print(f"Error updating order: {e}")
            return False

    def _map_to_model(self, row) -> Customer:
        """DB行をCustomerモデルへ変換"""
        if row is None: return None
        return Customer(
            id=row[0],
            label=row[1],
            attributes_json=row[2] if row[2] else "{}", # DBのJSON文字列をそのまま渡す
            color=row[3],
            display_order=row[4],
            is_active=bool(row[5])
        )
    
    def delete(self, customer_id: int) -> bool:
        """物理削除"""
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("DELETE FROM customer_presets WHERE id=?", (customer_id,))
            return True
        except Exception as e:
            print(f"Error deleting customer: {e}")
            return False
    
    def import_data(self, data: Dict) -> bool:
        """辞書データを取り込み (IDがあれば更新、なければ追加)"""
        try:
            cust = Customer.from_dict(data)
            if cust.id:
                if self.update(cust):
                    return True
                # 更新失敗(IDがない等)なら追加へフォールバック
            return self.add(cust)
        except Exception as e:
            print(f"Error importing customer: {e}")
            return False