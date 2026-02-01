from typing import List, Dict
from app.repositories.customer_repo import CustomerRepository
from app.repositories.log_repo import LogRepository
from app.models.customer import Customer

class CustomerService:
    def __init__(self, repo: CustomerRepository, log_repo: LogRepository = None):
        self.repo = repo
        self.log_repo = log_repo

    def get_all_customers(self) -> List[Customer]:
        return self.repo.fetch_all()

    def get_active_customers(self) -> List[Customer]:
        return self.repo.fetch_active()

    def add_customer(self, customer: Customer) -> bool:
        if self.repo.add(customer):
            if self.log_repo:
                self.log_repo.add_log("info", f"客層追加: {customer.label}")
            return True
        return False

    def update_customer(self, customer: Customer) -> bool:
        if self.repo.update(customer):
            if self.log_repo:
                self.log_repo.add_log("info", f"客層変更: {customer.label}")
            return True
        return False

    def delete_customer(self, customer: Customer) -> bool:
        if self.repo.delete(customer.id):
            if self.log_repo:
                self.log_repo.add_log("warning", f"客層完全削除: {customer.label}")
            return True
        return False

    def disable_customer(self, customer: Customer) -> bool:
        customer.is_active = False
        if self.repo.update(customer):
            if self.log_repo:
                self.log_repo.add_log("info", f"客層無効化: {customer.label}")
            return True
        return False

    def update_display_order(self, order_map: Dict[int, int]) -> bool:
        return self.repo.update_display_order(order_map)