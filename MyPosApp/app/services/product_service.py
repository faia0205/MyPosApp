from typing import List
from app.repositories.product_repo import ProductRepository
from app.models.product import Product

class ProductService:
    def __init__(self, repo: ProductRepository):
        self.repo = repo

    def get_active_products(self) -> List[Product]:
        """販売画面用: 有効な商品を取得"""
        return self.repo.fetch_active_products()

    def get_all_products(self) -> List[Product]:
        """商品一覧用"""
        return self.repo.fetch_all_as_models()