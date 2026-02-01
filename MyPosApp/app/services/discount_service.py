from typing import List
from app.repositories.discount_repo import DiscountRepository
from app.repositories.log_repo import LogRepository
from app.models.discount import DiscountRule

class DiscountService:
    def __init__(self, repo: DiscountRepository, log_repo: LogRepository):
        self.repo = repo
        self.log_repo = log_repo

    def get_all_rules(self) -> List[DiscountRule]:
        return self.repo.fetch_all_rules()

    def add_rule(self, rule: DiscountRule) -> bool:
        if self.repo.add(rule):
            self.log_repo.add_log("info", f"割引ルール追加: {rule.name}")
            return True
        return False

    def update_rule(self, rule: DiscountRule) -> bool:
        if self.repo.update(rule):
            self.log_repo.add_log("info", f"割引ルール更新: {rule.name}")
            return True
        return False

    def delete_rule(self, rule: DiscountRule) -> bool:
        if self.repo.delete(rule.id):
            self.log_repo.add_log("warning", f"割引ルール完全削除: {rule.name}")
            return True
        return False

    def disable_rule(self, rule: DiscountRule) -> bool:
        rule.is_active = False
        if self.repo.update(rule):
            self.log_repo.add_log("info", f"割引ルール無効化: {rule.name}")
            return True
        return False