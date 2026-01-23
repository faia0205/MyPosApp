from typing import List
from app.repositories.base_repo import BaseRepository
from app.models.expense import Expense

class ExpenseRepository(BaseRepository):
    """経費データのCRUDを担当"""

    def fetch_all(self) -> List[Expense]:
        with self.transaction() as (conn, cursor):
            cursor.execute("SELECT id, title, amount, created_at FROM expenses ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [Expense(id=r['id'], title=r['title'], amount=r['amount'], timestamp=r['created_at']) for r in rows]

    def get_total_amount(self) -> int:
        with self.transaction() as (conn, cursor):
            cursor.execute("SELECT SUM(amount) FROM expenses")
            res = cursor.fetchone()
            return res[0] if res[0] else 0

    def add(self, title: str, amount: int) -> bool:
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("INSERT INTO expenses (title, amount) VALUES (?, ?)", (title, amount))
            return True
        except Exception:
            return False

    def delete(self, expense_id: int) -> bool:
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
            return True
        except Exception:
            return False
    
    def update(self, expense: Expense) -> bool:
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("UPDATE expenses SET title=?, amount=?, created_at=? WHERE id=?",
                               (expense.title, expense.amount, expense.timestamp, expense.id))
            return True
        except Exception:
            return False