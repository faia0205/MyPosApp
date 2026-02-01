from typing import List
from app.repositories.payment_repo import PaymentRepository
from app.repositories.log_repo import LogRepository
from app.models.payment_method import PaymentMethod

class PaymentService:
    def __init__(self, repo: PaymentRepository, log_repo: LogRepository):
        self.repo = repo
        self.log_repo = log_repo

    def get_all_methods(self) -> List[PaymentMethod]:
        return self.repo.fetch_all()

    def add_method(self, method: PaymentMethod) -> bool:
        if self.repo.add(method):
            self.log_repo.add_log("info", f"支払方法追加: {method.name}")
            return True
        return False

    def update_method(self, method: PaymentMethod) -> bool:
        if self.repo.update(method):
            self.log_repo.add_log("info", f"支払方法更新: {method.name}")
            return True
        return False

    def delete_method(self, method: PaymentMethod) -> bool:
        if self.repo.delete(method.id):
            self.log_repo.add_log("warning", f"支払方法完全削除: {method.name}")
            return True
        return False

    def disable_method(self, method: PaymentMethod) -> bool:
        method.is_active = False
        if self.repo.update(method):
            self.log_repo.add_log("info", f"支払方法無効化: {method.name}")
            return True
        return False