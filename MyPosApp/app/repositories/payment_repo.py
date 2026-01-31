from typing import List, Optional
from app.repositories.base_repo import BaseRepository
from app.models.payment_method import PaymentMethod

class PaymentRepository(BaseRepository):
    """決済方法の設定・取得に関する責務を持つ"""

    def fetch_all(self) -> List[PaymentMethod]:
        """設定画面用: 全て取得"""
        with self.transaction() as (conn, cursor):
            cursor.execute("SELECT id, name, is_cash, is_active FROM payment_methods ORDER BY id")
            rows = cursor.fetchall()
            return [PaymentMethod(id=r['id'], name=r['name'], is_cash=bool(r['is_cash']), is_active=bool(r['is_active'])) for r in rows]

    def fetch_active(self) -> List[PaymentMethod]:
        """販売画面用: 有効なもののみ"""
        with self.transaction() as (conn, cursor):
            cursor.execute("SELECT id, name, is_cash, is_active FROM payment_methods WHERE is_active=1 ORDER BY id")
            rows = cursor.fetchall()
            return [PaymentMethod(id=r['id'], name=r['name'], is_cash=bool(r['is_cash']), is_active=bool(r['is_active'])) for r in rows]

    def add(self, method: PaymentMethod) -> bool:
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("INSERT INTO payment_methods (name, is_cash, is_active) VALUES (?, ?, ?)",
                               (method.name, int(method.is_cash), int(method.is_active)))
            return True
        except Exception:
            return False

    def update(self, method: PaymentMethod) -> bool:
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("UPDATE payment_methods SET name=?, is_cash=?, is_active=? WHERE id=?",
                               (method.name, int(method.is_cash), int(method.is_active), method.id))
            return True
        except Exception:
            return False
        
    def delete(self, payment_id: int) -> bool:
        """物理削除"""
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("DELETE FROM payment_methods WHERE id=?", (payment_id,))
            return True
        except Exception:
            return False