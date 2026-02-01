from typing import List, Dict
from app.repositories.product_repo import ProductRepository
from app.repositories.log_repo import LogRepository
from app.models.product import Product

class ProductService:
    def __init__(self, repo: ProductRepository, log_repo: LogRepository):
        self.repo = repo
        self.log_repo = log_repo

    def get_active_products(self) -> List[Product]:
        return self.repo.fetch_active_products()

    def get_all_products(self) -> List[Product]:
        return self.repo.fetch_all_as_models()

    def add_product(self, product: Product) -> bool:
        if self.repo.add_product(product):
            self.log_repo.add_log("info", f"商品追加: {product.name}")
            return True
        return False

    def update_product(self, product: Product) -> bool:
        if self.repo.update_product(product):
            self.log_repo.add_log("info", f"商品変更: {product.name}")
            return True
        return False

    def delete_product(self, product: Product) -> bool:
        # 完全削除
        if self.repo.delete_product(product.id):
            self.log_repo.add_log("warning", f"商品完全削除: {product.name}")
            return True
        return False

    def disable_product(self, product: Product) -> bool:
        # 無効化（論理削除的な扱い）
        product.is_active = False
        if self.repo.update_product(product):
            self.log_repo.add_log("info", f"商品無効化: {product.name}")
            return True
        return False

    def update_display_order(self, order_map: Dict[int, int]) -> bool:
        return self.repo.update_display_order(order_map)