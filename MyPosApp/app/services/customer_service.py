from typing import List
from app.repositories.customer_repo import CustomerRepository
from app.models.customer import Customer

class CustomerService:
    def __init__(self, repo: CustomerRepository):
        self.repo = repo

    def get_all_customers(self) -> List[Customer]:
        """全客層取得"""
        return self.repo.fetch_all()

    def get_active_customers(self) -> List[Customer]:
        """有効な客層のみ取得"""
        return self.repo.fetch_active()