from typing import List, Dict
import datetime
from app.repositories.base_repo import BaseRepository
from app.models.expense import Expense
from app.repositories.interfaces.master_data_repo import IMasterDataRepository

class ExpenseRepository(BaseRepository, IMasterDataRepository):
    """経費データのCRUDを担当"""

    def fetch_all(self) -> List[Expense]:
        with self.transaction() as (conn, cursor):
            cursor.execute("SELECT id, title, amount, created_at FROM expenses ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [Expense(id=r['id'], title=r['title'], amount=r['amount'], timestamp=r['created_at']) for r in rows]

    def get_total_expenses(self) -> int:
        with self.transaction() as (conn, cursor):
            cursor.execute("SELECT SUM(amount) FROM expenses")
            res = cursor.fetchone()
            return res[0] if res[0] else 0

    def add(self, title: str, amount: int) -> bool:
        try:
            t_delta = datetime.timedelta(hours=9)
            JST = datetime.timezone(t_delta, 'JST')
            now_jst = datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
            with self.transaction() as (conn, cursor):
                cursor.execute(
                    "INSERT INTO expenses (title, amount, created_at) VALUES (?, ?, ?)",
                    (title, amount, now_jst)
                )
                return True
        except Exception:
            return False

    def update(self, expense: Expense) -> bool:
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("UPDATE expenses SET title=?, amount=?, created_at=? WHERE id=?",
                               (expense.title, expense.amount, expense.timestamp, expense.id))
                # ★ 修正: 行数チェック
                return cursor.rowcount > 0
        except Exception:
            return False
            
    def delete(self, expense_id: int) -> bool:
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
                return True
        except Exception:
            return False

    # ★ 修正: IDを使ってUpsertを行うロジックに変更
    def import_data(self, data: Dict) -> bool:
        """辞書データを取り込み (Upsert)"""
        try:
            exp = Expense.from_dict(data)
            if exp.id:
                # 1. 更新を試みる
                if self.update(exp):
                    return True
                
                # 2. 更新失敗なら、IDとタイムスタンプを指定して強制挿入
                with self.transaction() as (conn, cursor):
                    cursor.execute(
                        "INSERT INTO expenses (id, title, amount, created_at) VALUES (?, ?, ?, ?)",
                        (exp.id, exp.title, exp.amount, exp.timestamp)
                    )
                return True
            else:
                # IDがない場合は通常追加
                return self.add(exp.title, exp.amount)
        except Exception as e:
            print(f"Error importing expense: {e}")
            return False

    def get_master_key(self) -> str:
        return "initial_expenses"

    def export_all_data(self) -> List[Dict]:
        models = self.fetch_all()
        return [p.to_dict() for p in models]

    def import_all_data(self, data_list: List[Dict]) -> bool:
        success = True
        for data in data_list:
            if not self.import_data(data):
                success = False
        return success