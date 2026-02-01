from typing import List
from app.repositories.expense_repo import ExpenseRepository
from app.repositories.log_repo import LogRepository
from app.models.expense import Expense

class ExpenseService:
    def __init__(self, repo: ExpenseRepository, log_repo: LogRepository):
        self.repo = repo
        self.log_repo = log_repo

    def get_all_expenses(self) -> List[Expense]:
        return self.repo.fetch_all()

    def add_expense(self, title: str, amount: int) -> bool:
        if self.repo.add(title, amount):
            self.log_repo.add_log("info", f"経費登録: {title} ¥{amount}")
            return True
        return False

    def update_expense(self, expense: Expense) -> bool:
        if self.repo.update(expense):
            self.log_repo.add_log("info", f"経費編集: ID{expense.id}")
            return True
        return False

    def delete_expense(self, expense: Expense) -> bool:
        if self.repo.delete(expense.id):
            self.log_repo.add_log("warning", f"経費削除: {expense.title}")
            return True
        return False