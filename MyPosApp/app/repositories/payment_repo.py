from typing import List, Optional, Dict
from app.repositories.base_repo import BaseRepository
from app.models.payment_method import PaymentMethod
from app.repositories.interfaces.master_data_repo import IMasterDataRepository

class PaymentRepository(BaseRepository, IMasterDataRepository):
    """決済方法の設定・取得に関する責務を持つ"""

    def fetch_all(self) -> List[PaymentMethod]:
        with self.transaction() as (conn, cursor):
            cursor.execute("SELECT id, name, is_cash, is_active FROM payment_methods ORDER BY id")
            rows = cursor.fetchall()
            return [PaymentMethod(id=r['id'], name=r['name'], is_cash=bool(r['is_cash']), is_active=bool(r['is_active'])) for r in rows]

    def fetch_active(self) -> List[PaymentMethod]:
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
                # ★ 修正: 更新件数が1件以上かを確認する
                return cursor.rowcount > 0
        except Exception:
            return False

    def delete(self, payment_id: int) -> bool:
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("DELETE FROM payment_methods WHERE id=?", (payment_id,))
                return True
        except Exception:
            return False

    def import_data(self, data: Dict) -> bool:
        """辞書データを取り込み"""
        try:
            pm = PaymentMethod.from_dict(data)
            # IDがある場合は更新を試みる
            if pm.id:
                if self.update(pm):
                    return True
                # 更新できなければ（IDがない場合など）、ID指定でのINSERTを試みる必要があるが、
                # ここでは簡易的に通常のadd（ID自動採番）にフォールバックさせる。
                # 完全な同期のためには「IDを指定してINSERT」が必要だが、SQLiteのAUTOINCREMENTとの兼ね合いもあるため、
                # 「IDが存在しないなら新規作成」という挙動にする。
            
            return self.add(pm)
        except Exception:
            return False

    def get_master_key(self) -> str:
        return "payment_methods"

    def export_all_data(self) -> List[Dict]:
        models = self.fetch_all()
        return [p.to_dict() for p in models]

    def import_all_data(self, data_list: List[Dict]) -> bool:
        success = True
        for data in data_list:
            if not self.import_data(data):
                success = False
        return success